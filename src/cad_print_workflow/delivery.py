"""Local, read-only source audit and staged multi-sheet delivery tools."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

import ezdxf
from pypdf import PdfReader, PdfWriter
from .cli import convert, inspect_file, visible


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory(filename):
    doc = ezdxf.readfile(filename)
    rows = []
    for e in doc.modelspace().query('DIMENSION'):
        if not visible(doc, e):
            continue
        row = {'handle': e.dxf.handle, 'type': e.dimtype, 'dimlfac': e.override().get('dimlfac', 1)}
        if e.dimtype in (0, 1, 3, 4):
            row['measured_mm'] = float(e.get_measurement())
        rows.append(row)
    return {'dimensions': rows, 'note': '这些是现有文件的数据，不是正确答案；expected必须来自教材或明确确认。'}


def load_job(filename):
    filename = Path(filename).resolve()
    job = json.loads(filename.read_text(encoding='utf8'))
    if job.get('version') != 1 or not isinstance(job.get('sheets'), list) or not 1 <= len(job['sheets']) <= 20:
        raise ValueError('作业需要version=1和1～20张图纸')
    ids = set()
    for sheet in job['sheets']:
        ident = sheet.get('id', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,50}', ident) or ident in ids:
            raise ValueError('每张图纸需要唯一的字母/数字编号')
        ids.add(ident)
        name = sheet.get('source')
        if not isinstance(name, str) or Path(name).is_absolute():
            raise ValueError('源文件应为作业清单所在目录下的相对路径')
        source = (filename.parent / name).resolve()
        if not source.is_relative_to(filename.parent) or source.suffix.lower() != '.dxf' or not source.is_file():
            raise ValueError('源DXF不存在或超出了作业目录')
        if sheet.get('geometry_reviewed') is not True:
            raise ValueError('请先核对图形、题意及尺寸来源，再将geometry_reviewed设为true')
        checks = sheet.get('dimensions', [])
        if not isinstance(checks, list):
            raise ValueError('dimensions必须是尺寸检查列表')
        seen = set()
        for c in checks:
            handle = c.get('handle')
            if not isinstance(handle, str) or handle in seen:
                raise ValueError('尺寸句柄缺失或重复')
            seen.add(handle)
            for key, default in [('expected', None), ('drawing_scale', 1), ('tolerance', .01)]:
                value = c.get(key, default)
                if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
                    raise ValueError('尺寸、绘图比例与容差必须是有限正数')
            if not isinstance(c.get('source'), str) or not c['source'].strip():
                raise ValueError('预期尺寸需要教材或用户确认来源，不能从当前错误标注自证')
    return job, filename.parent


def audit_job(filename):
    job, base = load_job(filename)
    reports = []
    for sheet in job['sheets']:
        file = base / sheet['source']
        info = inspect_file(file)
        d = ezdxf.readfile(file)
        errors, warnings, results = [], [], []
        if d.units != 4:
            errors.append('DXF未明确使用毫米单位')
        if d.audit().errors:
            errors.append('DXF内部审计失败')
        if info['unsupported_visible']:
            errors.append('包含不支持的可见图元：' + ','.join(info['unsupported_visible']))
        bounds = info['bounds']
        if not bounds or bounds[0][0] < -.01 or bounds[0][1] < -.01 or bounds[1][0] > 420.01 or bounds[1][1] > 297.01:
            errors.append('图形超出A3横向范围；不自动缩放')
        dimensions = {e.dxf.handle: e for e in d.modelspace().query('DIMENSION') if visible(d, e)}
        checked = {c['handle'] for c in sheet.get('dimensions', [])}
        if set(dimensions) - checked:
            errors.append('存在未列入检查清单的原生尺寸：' + ','.join(sorted(set(dimensions) - checked)))
        if not dimensions:
            warnings.append('无原生DIMENSION；文字或炸开的标注无法自动验证，须人工核对')
        for check in sheet.get('dimensions', []):
            e = dimensions.get(check['handle'])
            row = {**check, 'errors': []}
            fail = row['errors']
            if e is None:
                fail.append('找不到可打印的原生尺寸对象')
            elif e.dimtype not in (0, 1, 3, 4):
                fail.append('目前只核查线性、对齐、半径、直径尺寸')
            else:
                measured = float(e.get_measurement())
                factor = e.override().get('dimlfac', 1)
                value = measured * factor
                row.update(measured_mm=measured, dimlfac=factor, actual_mm=value)
                if not math.isfinite(factor) or factor <= 0 or abs(factor - 1 / check.get('drawing_scale', 1)) > 1e-8:
                    fail.append('标注换算因子与绘图比例不符')
                if not math.isfinite(value) or abs(value - check['expected']) > check.get('tolerance', .01):
                    fail.append('几何换算值与预期实际尺寸不符')
                template = e.dxf.get('text', '<>')
                if template.strip() and template.count('<>') != 1:
                    fail.append('尺寸文字被固定覆盖，可能掩盖几何错误')
                name = e.dxf.get('geometry')
                texts = [x.plain_text() for x in d.blocks[name].query('TEXT MTEXT')] if name in d.blocks else []
                numbers = re.findall(r'(?<![\d.])-?\d+(?:\.\d+)?', ' '.join(texts))
                row['cached_text'] = texts
                if len(numbers) != 1 or abs(float(numbers[0]) - check['expected']) > check.get('tolerance', .01):
                    fail.append('缓存显示文字与预期尺寸不一致或无法可靠识别')
            if fail:
                errors.append(check['handle'] + '：' + '；'.join(fail))
            results.append(row)
        reports.append({'id': sheet['id'], 'title': sheet.get('title', sheet['id']), 'source': sheet['source'],
                        'sha256': digest(file), 'dimensions': results, 'errors': errors, 'warnings': warnings})
    return {'version': 1, 'passed': all(not r['errors'] for r in reports), 'visual_review_required': True,
            'scope': '仅核查清单中的原生尺寸及其显示缓存；不证明尺寸关联到了正确轮廓。', 'sheets': reports}


def build_job(filename, output, font=None):
    output = Path(output)
    if output.exists():
        raise ValueError('交付目录已存在，请使用新目录；不覆盖已有文件')
    report = audit_job(filename)
    if not report['passed']:
        raise ValueError('作业检查未通过：' + '；'.join(e for s in report['sheets'] for e in s['errors']))
    job, base = load_job(filename)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        stage = Path(temporary) / 'delivery'
        stage.mkdir()
        writer = PdfWriter()
        for sheet, checked in zip(job['sheets'], report['sheets']):
            src = base / sheet['source']
            target = stage / (sheet['id'] + '.dxf')
            shutil.copyfile(src, target)
            if digest(target) != checked['sha256']:
                raise ValueError('源文件在核查后发生变化，请重新检查')
            convert(target, stage / (sheet['id'] + '.pdf'), font=font, preview=True)
            writer.append(PdfReader(stage / (sheet['id'] + '.pdf')))
        writer.write(stage / 'A3-all.pdf')
        (stage / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
        (stage / 'README.txt').write_text('A3横向，实际大小100%，关闭适应纸张。\n请逐页检查PNG预览及PDF；检查通过后再执行package --confirm-visual。\n', encoding='utf8')
        hashes = {p.name: digest(p) for p in stage.iterdir() if p.is_file()}
        (stage / 'delivery.json').write_text(json.dumps({'version': 1, 'status': 'awaiting_visual_review', 'files': hashes}, indent=2), encoding='utf8')
        stage.rename(output)
    return {'directory': str(output), 'sheets': len(job['sheets']), 'status': 'awaiting_visual_review'}


def package_job(directory, confirm_visual=False):
    if not confirm_visual:
        raise ValueError('请先逐页检查预览，再使用--confirm-visual确认')
    directory = Path(directory)
    manifest = json.loads((directory / 'delivery.json').read_text())
    files = manifest.get('files', {})
    if manifest.get('version') != 1 or not files:
        raise ValueError('无有效交付记录')
    for name, expected in files.items():
        p = directory / name
        if Path(name).name != name or p.is_symlink() or not p.is_file() or digest(p) != expected:
            raise ValueError('交付文件缺失或在检查后被修改，请重新构建：' + name)
    if not json.loads((directory / 'audit.json').read_text())['passed']:
        raise ValueError('审计未通过')
    output = directory / 'delivery.zip'
    if output.exists():
        raise ValueError('交付压缩包已存在，不覆盖')
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(directory / name, name)
        archive.writestr('review.json', json.dumps({'visual_review_confirmed': True, 'files': files}, ensure_ascii=False, indent=2))
    return {'archive': str(output), 'visual_review_confirmed': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description='整套A3作业检查、打印与交付（本地运行，不上传文件）')
    sub = parser.add_subparsers(dest='command', required=True)
    listing = sub.add_parser('inventory'); listing.add_argument('input')
    check = sub.add_parser('check'); check.add_argument('job')
    build = sub.add_parser('build'); build.add_argument('job'); build.add_argument('-o', '--output', required=True); build.add_argument('--font')
    pack = sub.add_parser('package'); pack.add_argument('directory'); pack.add_argument('--confirm-visual', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'inventory':
            result = inventory(args.input)
        elif args.command == 'check':
            result = audit_job(args.job)
        elif args.command == 'build':
            result = build_job(args.job, args.output, args.font)
        else:
            result = package_job(args.directory, args.confirm_visual)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == 'check' and not result['passed']:
            parser.exit(2)
    except (ValueError, OSError, ezdxf.DXFError) as exc:
        parser.exit(2, f'错误：{exc}\n')

if __name__ == '__main__':
    main()
