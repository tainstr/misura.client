
import numpy as np
from misura.canon.indexer import SharedFile
from misura.canon.reference import get_node_reference

try:
    import pyqtgraph as pg
    import pyqtgraph.opengl as gl
except:
    pg = False
    gl = False

STEPS = np.array([0.0, 0.33, 0.66, 1.0])
CLRS =           ['b', 'r', 'y', 'w']

if pg:
    clrmp = pg.ColorMap(STEPS, np.array([pg.colorTuple(pg.Color(c)) for c in CLRS]))

#TODO: parametrize start, end, max_layers
#TODO: step by time/temperature
#TODO: write temperature labels
def read_file(profile, start=3500, end=-1, max_layers = 1000, cut=0):
    xs = []
    ys = []
    zs = []
    colors = []

    c = 0.
    n = len(profile)
    if end<0:
        end += n
    n = end-start+1
    step = max(n//max_layers,1)
    tot = n//step
    level_step = 255./tot
    fz = 0.0009
    z = -fz*tot/2
    
    for i in range(start, end, step):
        print 'Processing', z, c, tot
        t, ((w,h), x, y) = profile[i]
        x = x.astype(np.float32)/700
        y = y.astype(np.float32)/700
        if cut:
            x=x[cut:-cut]
            y=y[cut:-cut]
        x-=x.mean()
        xs.append(x)
        ys.append(-y)
        zs.append(-z)
        col = list(clrmp.map(1.*c/tot))
        col[-1] = int(200-(col[0]+col[1]+col[2])/4)
        colors.append(col)
        #colors.append(col)
        # Should be calc depending on shot height
        z+=fz
        c+=1
    return xs,ys,zs, colors



def plot_line(x,y,z, color='w'):
    # first line
    p=np.array([z,x,y])
    p=p.transpose() 
    C=pg.glColor(color)
    #plt = gl.GLScatterPlotItem(pos=p, color=C, size =2.5)
    plt = gl.GLLinePlotItem(pos=p, color=C, width =1.5, antialias=True)
    return plt

def add_grids(view):
    ## create three grids, add each to the view
    xgrid = gl.GLGridItem()
    ygrid = gl.GLGridItem()
    zgrid = gl.GLGridItem()
    view.addItem(xgrid)
    view.addItem(ygrid)
    view.addItem(zgrid)

    ## rotate x and y grids to face the correct direction
    xgrid.rotate(90, 0, 1, 0)
    ygrid.rotate(90, 1, 0, 0)


def plot3d(xs,ys,zs, colors, start=0, end=-1, step=1):
    w = gl.GLViewWidget()
    for i, x in enumerate(xs):
        sampled_x = x[start:end:step]
        sampled_y = ys[i][start:end:step]-ys[i][0]
        z = np.ones(len(sampled_x))*zs[i]
        plt = plot_line(sampled_x,sampled_y, z, color=colors[i] )
        w.addItem(plt)
    #add_grids(w)
    ax = gl.GLAxisItem()
    w.addItem(ax)
    ##w.pan(0,0,0)
    return w

def surface3d(xs,ys,zs, colors, start=0, end=-1, step=1):
    w = gl.GLViewWidget()
    nx, ny, nz = [], [], []
    for i, x in enumerate(xs):
        sampled_x = x[start:end:step]
        sampled_y = ys[i][start:end:step]-ys[i][0]
        z = np.ones(len(sampled_x))*zs[i]
        nx.append(sampled_x)
        ny.append(sampled_y)
        nz.append(z)
        
    verts = np.array([nx[0], ny[0], nz[0]]).transpose()
    faces = []
    fcolors = []
    vcolors = [colors[0]]*len(verts)
    vi = 0
    for i in range(1, len(nx)):
        nverts = np.array([nx[i], ny[i], nz[i]]).transpose()
        vj = len(verts)
        for j, v in enumerate(nverts):
            if j<len(nverts)-1:
                faces += [[vi+j, vj+j, vj+j+1],
                          [vi+j, vi+j+1, vj+j+1]]
                
                fcolors += [colors[i]]*2
        verts = np.concatenate((verts, nverts))
        vcolors += [colors[i]]*len(nverts)
        vi = vj
    
    mesh = gl.MeshData(verts, np.array(faces), faceColors=fcolors, vertexColors=vcolors)
    plt = gl.GLMeshItem(meshdata=mesh, drawFaces=True, drawEdges=False)
    
    w.addItem(plt)
    #add_grids(w)
    ax = gl.GLAxisItem()
    w.addItem(ax)
    return w

def extrude(f, data_path, cut=0):
    prf = get_node_reference(f, data_path)
    #prf = get_node_reference(f, '/hsm/sample0/profile')
    xs,ys,zs, colors = read_file(prf, cut=cut)
    w= plot3d(xs,ys,zs, colors)
    return w
    
if __name__=='__main__':
    test_path = '/home/daniele/MisuraData/hsm/BORAX powder 10 C min.h5'
    data_path = '/hsm/sample0/profile'
    cut = 200
    #test_path = '/home/daniele/MisuraData/horizontal/profiles/System Interbau 80 1400.h5'
    #data_path = '/horizontal/sample0/Right/profile'
    app=pg.QtGui.QApplication([])
    f = SharedFile(test_path)
    w = extrude(f, data_path)
    w.show()
    pg.QtGui.QApplication.exec_()



