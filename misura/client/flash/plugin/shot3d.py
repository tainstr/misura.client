import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
#import vispy.mpl_plot as plt

def plot3d(xs,ys,zs, colors, start=8000, end=15000, step=20):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    for i, x in enumerate(xs):
        ax.scatter(x[start:end:step],ys[i][start:end:step]-ys[i][0],zs[i], color=colors[i], s=2)
    plt.show()
    
#plot3d([np.linspace(1,5,10)],[np.linspace(1,5,10)],[np.linspace(1,5,10)])
cmap = ['#0000ff',  '#0080ff', '#00ff40', '#bfff00', '#ff8000', '#ff0000']
test_path = '/home/daniele/MisuraData/flash/1322MOshinythin.h5'
from misura.canon.indexer import SharedFile
def read_file():
    f = SharedFile(test_path)
    xs = []
    ys = []
    zs = []
    colors = []
    z = 0
    segdict = f.test.root.flash.sample0._v_groups
    segnames = segdict.keys()
    segnames = sorted(segnames, key=lambda a: int(a[1:]))
    print(segnames)
    c = 0
    for seg_name in segnames:
        seg_node = segdict[seg_name]
        for shot_name, shot_node in seg_node._v_groups.iteritems():
            print('Processing', shot_node._v_pathname)
            x = shot_node.raw.cols.t[:]
            xs.append(x)
            y = shot_node.raw.cols.v[:]
            ys.append(y)
            zs.append(z)
            colors.append(cmap[c])
            z+=1
        c+=1
    return xs,ys,zs, colors
xs,ys,zs, colors = read_file()
plot3d(xs,ys,zs, colors)
   
