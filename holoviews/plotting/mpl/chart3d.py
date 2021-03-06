from distutils.version import LooseVersion

import numpy as np
import param
import matplotlib as mpl
import matplotlib.cm as cm

from ...core import Dimension
from ...core.util import basestring
from ..util import map_colors
from .element import ColorbarPlot
from .chart import PointPlot


class Plot3D(ColorbarPlot):
    """
    Plot3D provides a common baseclass for mplot3d based
    plots.
    """

    azimuth = param.Integer(default=-60, bounds=(-180, 180), doc="""
        Azimuth angle in the x,y plane.""")

    elevation = param.Integer(default=30, bounds=(0, 180), doc="""
        Elevation angle in the z-axis.""")

    distance = param.Integer(default=10, bounds=(7, 15), doc="""
        Distance from the plotted object.""")

    disable_axes = param.Boolean(default=False, doc="""
        Disable all axes.""")

    bgcolor = param.String(default='white', doc="""
        Background color of the axis.""")

    labelled = param.List(default=['x', 'y', 'z'], doc="""
        Whether to plot the 'x', 'y' and 'z' labels.""")

    projection = param.ObjectSelector(default='3d', objects=['3d'], doc="""
        The projection of the matplotlib axis.""")

    show_frame = param.Boolean(default=False, doc="""
        Whether to draw a frame around the figure.""")

    show_grid = param.Boolean(default=True, doc="""
        Whether to draw a grid in the figure.""")

    xaxis = param.ObjectSelector(default='fixed',
                                 objects=['fixed', None], doc="""
        Whether and where to display the xaxis.""")

    yaxis = param.ObjectSelector(default='fixed',
                                 objects=['fixed', None], doc="""
        Whether and where to display the yaxis.""")

    zaxis = param.ObjectSelector(default='fixed',
                                 objects=['fixed', None], doc="""
        Whether and where to display the yaxis.""")

    def _finalize_axis(self, key, **kwargs):
        """
        Extends the ElementPlot _finalize_axis method to set appropriate
        labels, and axes options for 3D Plots.
        """
        axis = self.handles['axis']
        self.handles['fig'].set_frameon(False)
        axis.grid(self.show_grid)
        axis.view_init(elev=self.elevation, azim=self.azimuth)
        axis.dist = self.distance

        if self.xaxis is None:
            axis.w_xaxis.line.set_lw(0.)
            axis.w_xaxis.label.set_text('')
        if self.yaxis is None:
            axis.w_yaxis.line.set_lw(0.)
            axis.w_yaxis.label.set_text('')
        if self.zaxis is None:
            axis.w_zaxis.line.set_lw(0.)
            axis.w_zaxis.label.set_text('')
        if self.disable_axes:
            axis.set_axis_off()

        if LooseVersion(mpl.__version__) <= '1.5.9':
            axis.set_axis_bgcolor(self.bgcolor)
        else:
            axis.set_facecolor(self.bgcolor)
        return super(Plot3D, self)._finalize_axis(key, **kwargs)


    def _draw_colorbar(self, dim=None):
        element = self.hmap.last
        artist = self.handles.get('artist', None)

        fig = self.handles['fig']
        ax = self.handles['axis']
        # Get colorbar label
        if dim is None:
            dim = element.vdims[0]

        elif not isinstance(dim, Dimension):
            dim = element.get_dimension(dim)
        label = str(dim)
        cbar = fig.colorbar(artist, shrink=0.7, ax=ax)
        self.handles['cax'] = cbar.ax
        self._adjust_cbar(cbar, label, dim)



class Scatter3DPlot(Plot3D, PointPlot):
    """
    Subclass of PointPlot allowing plotting of Points
    on a 3D axis, also allows mapping color and size
    onto a particular Dimension of the data.
    """

    color_index = param.ClassSelector(default=4, class_=(basestring, int),
                                      allow_None=True, doc="""
      Index of the dimension from which the color will the drawn""")

    size_index = param.ClassSelector(default=3, class_=(basestring, int),
                                     allow_None=True, doc="""
      Index of the dimension from which the sizes will the drawn.""")

    _plot_methods = dict(single='scatter')

    def get_data(self, element, ranges, style):
        xs, ys, zs = (element.dimension_values(i) for i in range(3))
        self._compute_styles(element, ranges, style)
        # Temporary fix until color handling is deterministic in mpl+py3
        if not element.get_dimension(self.color_index) and 'c' in style:
            color = style.pop('c')
            if LooseVersion(mpl.__version__) >= '1.5':
                style['color'] = color
            else:
                style['facecolors'] = color
        return (xs, ys, zs), style, {}

    def update_handles(self, key, axis, element, ranges, style):
        artist = self.handles['artist']
        artist._offsets3d, style, _ = self.get_data(element, ranges, style)
        cdim = element.get_dimension(self.color_index)
        if cdim and 'cmap' in style:
            clim = style['vmin'], style['vmax']
            cmap = cm.get_cmap(style['cmap'])
            artist._facecolor3d = map_colors(style['c'], clim, cmap, hex=False)
        if element.get_dimension(self.size_index):
            artist.set_sizes(style['s'])



class SurfacePlot(Plot3D):
    """
    Plots surfaces wireframes and contours in 3D space.
    Provides options to switch the display type via the
    plot_type parameter has support for a number of
    styling options including strides and colors.
    """

    colorbar = param.Boolean(default=False, doc="""
        Whether to add a colorbar to the plot.""")

    plot_type = param.ObjectSelector(default='surface',
                                     objects=['surface', 'wireframe',
                                              'contour'], doc="""
        Specifies the type of visualization for the Surface object.
        Valid values are 'surface', 'wireframe' and 'contour'.""")

    style_opts = ['antialiased', 'cmap', 'color', 'shade',
                  'linewidth', 'facecolors', 'rstride', 'cstride',
                  'norm']

    def init_artists(self, ax, plot_data, plot_kwargs):
        if self.plot_type == "wireframe":
            artist = ax.plot_wireframe(*plot_data, **plot_kwargs)
        elif self.plot_type == "surface":
            artist = ax.plot_surface(*plot_data, **plot_kwargs)
        elif self.plot_type == "contour":
            artist = ax.contour3D(*plot_data, **plot_kwargs)
        return {'artist': artist}

    def get_data(self, element, ranges, style):
        mat = element.data
        rn, cn = mat.shape
        l, b, _, r, t, _ = self.get_extents(element, ranges)
        r, c = np.mgrid[l:r:(r-l)/float(rn), b:t:(t-b)/float(cn)]
        self._norm_kwargs(element, ranges, style, element.vdims[0])
        return (r, c, mat), style, {}
            


class TrisurfacePlot(Plot3D):
    """
    Plots a trisurface given a Trisurface element, containing
    X, Y and Z coordinates.
    """

    colorbar = param.Boolean(default=False, doc="""
        Whether to add a colorbar to the plot.""")

    style_opts = ['cmap', 'color', 'shade', 'linewidth', 'edgecolor',
                  'norm']

    _plot_methods = dict(single='plot_trisurf')

    def get_data(self, element, ranges, style):
        dims = element.dimensions()
        self._norm_kwargs(element, ranges, style, dims[2])
        x, y, z = [element.dimension_values(d) for d in dims]
        return (x, y, z), style, {}
