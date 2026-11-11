from __future__ import annotations
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile

import ezdxf
from ezdxf import bbox, path
from ezdxf.addons import MTextExplode, text2path
from ezdxf.disassemble import recursive_decompose
from ezdxf.fonts import fonts
from ezdxf.lldxf.encoding import decode_dxf_unicode
from fontTools.ttLib import TTFont
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

SUPPORTED = {'LINE', 'ARC', 'CIRCLE', 'LWPOLYLINE', 'POLYLINE', 'SOLID', 'TEXT', 'MTEXT', 'DIMENSION'}


def visible(doc, ent):
    layer = doc.layers.get(ent.dxf.layer)
    return not (layer.is_off() or layer.is_frozen() or not layer.dxf.get('plot', 1) or ent.dxf.get('invisible', 0))


def inspect_file(filename):
    doc = ezdxf.readfile(filename)
    space = doc.modelspace()
    visible_entities = [e for e in space if visible(doc, e)]
    bounds = bbox.extents(visible_entities)
    return {
        'units_code': doc.units,
        'entity_counts': dict(Counter(e.dxftype() for e in space)),
        'visible_count': len(visible_entities),
        'unsupported_visible': sorted({e.dxftype() for e in visible_entities} - SUPPORTED),
        'bounds': [list(bounds.extmin), list(bounds.extmax)] if bounds.has_data else None,
        'layers': [{'name': x.dxf.name, 'off': x.is_off(), 'frozen': x.is_frozen(),
                    'plot': bool(x.dxf.get('plot', 1)), 'lineweight': x.dxf.lineweight} for x in doc.layers],
        'note': 'Dimension values and drafting correctness require review; inspect does not change geometry.'
    }


def select_font(requested):
    if requested:
        candidate = Path(requested).expanduser()
        if not candidate.is_file():
            raise ValueError(f'Font file not found: {candidate}')
    else:
        options = [Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
                   Path('C:/Windows/Fonts/arial.ttf'),
                   Path('/System/Library/Fonts/Supplemental/Arial.ttf')]
        candidate = next((p for p in options if p.is_file()), None)
        if candidate is None:
            raise ValueError('Supply --font /path/to/font.ttf (TrueType, including all required glyphs).')
    if candidate.suffix.lower() != '.ttf':
        raise ValueError('Use a standalone .ttf font; TTC collections and SHX are not supported.')
    fonts.font_manager.build([str(candidate.parent)])
    face = fonts.get_font_face(candidate.name)
    if face.filename.lower() != candidate.name.lower():
        raise ValueError('ezdxf could not load the selected font; refusing silent substitution.')
    with TTFont(candidate) as f:
        cmap = f.getBestCmap()
    return candidate, cmap


def prepare(filename, font=None):
    doc = ezdxf.readfile(filename)
    if doc.units != 4:
        raise ValueError('Only explicitly millimetre DXF ($INSUNITS=4) is supported. Set/convert units first.')
    if doc.audit().errors:
        raise ValueError('DXF audit has errors; repair the drawing before printing.')
    model = doc.modelspace()
    for ent in list(model):
        if not visible(doc, ent):
            model.delete_entity(ent)
            continue
        if ent.dxftype() not in SUPPORTED:
            raise ValueError(f'Unsupported visible entity: {ent.dxftype()}; convert it explicitly first.')
        if ent.dxftype() == 'DIMENSION':
            if ent.dxf.get('geometry') not in doc.blocks:
                raise ValueError('Dimension has no cached display block; render/save it in CAD first.')
            children = list(recursive_decompose([ent]))
            if not children:
                raise ValueError('Empty dimension display block.')
            for child in children:
                copy = child.copy()
                if copy.dxf.layer == '0':
                    copy.dxf.layer = ent.dxf.layer
                model.add_entity(copy)
            model.delete_entity(ent)
    with MTextExplode(model) as exploder:
        for ent in list(model.query('MTEXT')):
            exploder.explode(ent)
    texts = list(model.query('TEXT'))
    for ent in texts:
        ent.dxf.text = decode_dxf_unicode(ent.dxf.text)
    chosen = None
    if texts:
        chosen, cmap = select_font(font)
        doc.styles.new('PRINT_FONT', dxfattribs={'font': chosen.name}) if 'PRINT_FONT' not in doc.styles else None
        doc.styles.get('PRINT_FONT').dxf.font = chosen.name
        missing = sorted({c for e in texts for c in e.plain_text() if not c.isspace() and ord(c) not in cmap})
        if missing:
            raise ValueError('Selected font lacks glyphs: ' + ''.join(missing) + '; provide --font with coverage.')
        for ent in texts:
            ent.dxf.style = 'PRINT_FONT'
    items = []
    for ent in model:
        if not visible(doc, ent):
            continue
        typ = ent.dxftype()
        if typ not in SUPPORTED - {'MTEXT', 'DIMENSION'}:
            raise ValueError(f'Unsupported expanded entity: {typ}')
        extrusion = ent.dxf.get('extrusion', (0, 0, 1))
        if tuple(extrusion) != (0, 0, 1):
            raise ValueError('Non-default extrusion/3D geometry is unsupported.')
        eb = bbox.extents([ent])
        if eb.has_data and max(abs(eb.extmin.z), abs(eb.extmax.z)) > 1e-7:
            raise ValueError('Non-zero elevation/3D geometry is unsupported.')
        layer = doc.layers.get(ent.dxf.layer)
        weight = ent.dxf.get('lineweight', -1)
        if weight < 0:
            weight = layer.dxf.get('lineweight', 25)
        width = max((weight if weight >= 0 else 25) / 100, .13)
        name = ent.dxf.get('linetype', 'BYLAYER')
        if name.upper() == 'BYLAYER':
            name = layer.dxf.linetype
        if name.upper() == 'BYBLOCK':
            name = 'CONTINUOUS'
        lt = doc.linetypes.get(name)
        if any(t.code == 74 and t.value != 0 for t in lt.pattern_tags.tags):
            raise ValueError('Complex linetypes with text/shapes are unsupported.')
        factor = doc.header.get('$LTSCALE', 1) * ent.dxf.get('ltscale', 1)
        dash = [max(abs(v) * factor, .08) for v in lt.simplified_line_pattern()]
        item = {'type': typ, 'width': width, 'dash': dash}
        if typ == 'LINE':
            item.update(a=list(ent.dxf.start)[:2], b=list(ent.dxf.end)[:2])
        elif typ in ('ARC', 'CIRCLE'):
            item.update(center=list(ent.dxf.center)[:2], radius=ent.dxf.radius)
            if typ == 'ARC':
                item.update(start=ent.dxf.start_angle, end=ent.dxf.end_angle)
        elif typ == 'SOLID':
            item['points'] = [list(v)[:2] for v in ent.vertices()]
        elif typ in ('LWPOLYLINE', 'POLYLINE'):
            if ent.has_width:
                raise ValueError('Wide polylines are unsupported; convert them to outlines first.')
            item['points'] = [list(v)[:2] for v in path.make_path(ent).flattening(.003)]
            item['closed'] = bool(ent.is_closed)
        elif typ == 'TEXT':
            item['paths'] = [[list(v)[:2] for v in p.flattening(.003)] for p in text2path.make_paths_from_entity(ent)]
            if ent.plain_text().strip() and not item['paths']:
                raise ValueError('Text conversion produced no visible glyphs.')
        items.append(item)
    bounds = bbox.extents(model)
    if not items or not bounds.has_data:
        raise ValueError('No printable geometry.')
    return items, bounds, chosen


def convert(source, output, font=None, width=420, height=297, origin=(0, 0), force=False, preview=False):
    source, output = Path(source), Path(output)
    report_path = output.with_suffix('.report.json')
    png_path = output.with_suffix('.png')
    if output.suffix.lower() != '.pdf':
        raise ValueError('Output must have a .pdf extension.')
    if source.resolve() == output.resolve():
        raise ValueError('Input and output must differ.')
    if width <= 0 or height <= 0 or not all(math.isfinite(v) for v in (width, height, *origin)):
        raise ValueError('Page size/origin must be finite and page dimensions positive.')
    targets = [output, report_path] + ([png_path] if preview else [])
    if not force and any(p.exists() for p in targets):
        raise ValueError('Output already exists; select a new name or explicitly pass --force.')
    if preview and not shutil.which('pdftoppm'):
        raise ValueError('--preview requires Poppler pdftoppm on PATH.')
    items, bounds, selected = prepare(source, font)
    ox, oy = origin
    if (bounds.extmin.x < ox - .01 or bounds.extmin.y < oy - .01 or
        bounds.extmax.x > ox + width + .01 or bounds.extmax.y > oy + height + .01):
        raise ValueError('Geometry exceeds page at 1:1. Adjust --origin/--width/--height or drawing layout; no auto-fit applied.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        pdf = Path(temp) / 'drawing.pdf'
        c = canvas.Canvas(str(pdf), pagesize=(width*mm, height*mm), pageCompression=1)
        c.setTitle('Engineering drawing'); c.scale(mm, mm); c.translate(-ox, -oy)
        c.setStrokeColorRGB(0, 0, 0); c.setFillColorRGB(0, 0, 0); c.setLineCap(0); c.setLineJoin(0)
        for x in items:
            c.setLineWidth(x['width']); c.setDash(x['dash']); typ = x['type']
            if typ == 'LINE':
                c.line(*x['a'], *x['b'])
            elif typ == 'CIRCLE':
                c.circle(*x['center'], x['radius'], stroke=1, fill=0)
            elif typ == 'ARC':
                cx, cy = x['center']; r = x['radius']
                c.arc(cx-r, cy-r, cx+r, cy+r, startAng=x['start'], extent=(x['end']-x['start']) % 360)
            else:
                p = c.beginPath()
                loops = x['paths'] if typ == 'TEXT' else [x['points']]
                for points in loops:
                    if not points:
                        continue
                    p.moveTo(*points[0])
                    for v in points[1:]:
                        p.lineTo(*v)
                    if typ in ('TEXT', 'SOLID') or x.get('closed'):
                        p.close()
                fill = typ in ('TEXT', 'SOLID')
                c.drawPath(p, stroke=int(not fill), fill=int(fill), fillMode=0)
        c.showPage(); c.save()
        reader = PdfReader(pdf)
        box = reader.pages[0].mediabox
        if len(reader.pages) != 1 or abs(float(box.width)/mm-width) > .001 or abs(float(box.height)/mm-height) > .001:
            raise ValueError('PDF page-size validation failed.')
        if preview:
            subprocess.run(['pdftoppm', '-scale-to', '1680', '-png', '-singlefile', str(pdf), str(Path(temp)/'preview')], check=True, capture_output=True)
        report = {'page_mm': [width, height], 'origin_mm': list(origin), 'paper_scale': 1,
                  'rendered_entities': dict(Counter(x['type'] for x in items)),
                  'text_font': selected.name if selected else None,
                  'warnings': ['Monochrome export; lineweights below 0.13 mm are raised to 0.13 mm.',
                               'Text is outlined using the selected font; inspect spacing and glyphs.',
                               'Cached dimension display is preserved; numerical correctness is not verified.',
                               'Paper-space layouts, embedded images, 3D and complex linetypes are not supported.',
                               'Entities on the exact page edge can lose half their stroke; retain a printing margin.'],
                  'visual_review_required': True}
        pdf.replace(output)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        if preview:
            (Path(temp)/'preview.png').replace(png_path)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='Inspect DXF and print 2D millimetre geometry to vector PDF without automatic scaling.')
    sub = parser.add_subparsers(dest='command', required=True)
    ins = sub.add_parser('inspect'); ins.add_argument('input')
    exp = sub.add_parser('export'); exp.add_argument('input'); exp.add_argument('-o', '--output', required=True)
    exp.add_argument('--font'); exp.add_argument('--width', type=float, default=420); exp.add_argument('--height', type=float, default=297)
    exp.add_argument('--origin', type=float, nargs=2, default=(0, 0)); exp.add_argument('--force', action='store_true'); exp.add_argument('--preview', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'inspect':
            result = inspect_file(args.input)
        else:
            result = convert(args.input, args.output, args.font, args.width, args.height, args.origin, args.force, args.preview)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, ezdxf.DXFError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f'Error: {exc}\n')

if __name__ == '__main__':
    main()
