"""Create synthetic input, independent of personal drawings."""
import ezdxf

doc = ezdxf.new('R2000'); doc.units = 4
m = doc.modelspace()
doc.layers.new('THIN', dxfattribs={'lineweight': 25})
doc.layers.new('OUTLINE', dxfattribs={'lineweight': 50})
m.add_lwpolyline([(25,5),(415,5),(415,292),(25,292)], close=True, dxfattribs={'layer':'OUTLINE'})
for y in (185,200):m.add_line((40,y),(200,y),dxfattribs={'layer':'THIN'})
m.add_circle((300,200),36,dxfattribs={'layer':'OUTLINE'})
m.add_arc((300,100),25,15,170)
m.add_text('A3 / 1:1',dxfattribs={'height':3.5,'insert':(40,270)})
m.add_linear_dim(base=(40,175),p1=(40,185),p2=(200,185),override={'dimtxt':3.5}).render()
doc.saveas('demo.dxf')
print('Created demo.dxf')
