import pandas as pd
from .geometry import GeometryDtype
from .geoseries import GeoSeries
from ._optional_imports import gp


def _maybe_geo_frame(data, **kwargs):
    try:
        return GeoDataFrame(data, **kwargs)
    except ValueError:
        # No geometry compatible columns
        return pd.DataFrame(data, **kwargs)


class GeoDataFrame(pd.DataFrame):
    # properties to propagate
    _metadata = ['_geometry']

    def __init__(self, data=None, index=None, geometry=None, **kwargs):
        # Call pandas constructor, always copy
        kwargs.pop("copy", None)
        super(GeoDataFrame, self).__init__(data, index=index, copy=True, **kwargs)

        # Replace pd.Series of GeometryArrays with GeoSeries.
        first_geometry_col = None
        for col in self.columns:
            if (isinstance(self[col].dtype, GeometryDtype) or
                    gp and isinstance(self[col].dtype, gp.array.GeometryDtype)):
                self[col] = GeoSeries(self[col])
                first_geometry_col = first_geometry_col or col

        if first_geometry_col is None:
            raise ValueError(
                "A spatialpandas GeoDataFrame must contain at least one spatialpandas "
                "GeometryArray column"
            )

        if geometry is None:
            if isinstance(data, GeoDataFrame) and data._has_valid_geometry():
                geometry = data._geometry
            else:
                geometry = first_geometry_col

        self._geometry = None
        if geometry is not None:
            self.set_geometry(geometry, inplace=True)

    @property
    def _constructor(self):
        return _maybe_geo_frame

    @property
    def _constructor_sliced(self):
        from .geoseries import _maybe_geo_series
        return _maybe_geo_series

    def set_geometry(self, geometry, inplace=False):
        if (geometry not in self or
                not isinstance(self[geometry].dtype, GeometryDtype)):
            raise ValueError(
                "The geometry argument must be the name of a spatialpandas "
                "geometry column in the spatialpandas GeoDataFrame"
            )

        if inplace:
            self._geometry = geometry
            return self
        else:
            return GeoDataFrame(self, geometry=geometry)

    def _has_valid_geometry(self):
        if (self._geometry is not None and
                self._geometry in self and
                isinstance(self[self._geometry].dtype, GeometryDtype)):
            return True
        else:
            return False

    @property
    def geometry(self):
        if not self._has_valid_geometry():
            raise ValueError(
                "GeoDataFrame has no active geometry column.\n"
                "The active geometry column should be set using the set_geometry "
                "method."
            )

        return self[self._geometry]

    def to_geopandas(self):
        from geopandas import GeoDataFrame as gp_GeoDataFrame
        gdf = gp_GeoDataFrame(
            {col: s.array.to_geopandas() if isinstance(s.dtype, GeometryDtype) else s
             for col, s in self.items()},
            index=self.index,
        )
        if self._has_valid_geometry():
            gdf.set_geometry(self._geometry, inplace=True)
        return gdf

    @property
    def cx(self):
        from .geometry.base import _CoordinateIndexer
        return _CoordinateIndexer(
            self.geometry.array, parent=self
        )
