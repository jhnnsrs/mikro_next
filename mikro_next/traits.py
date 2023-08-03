"""
Traits for mikro_next

Traits are mixins that are added to every graphql type that exists on the mikro schema.
We use them to add functionality to the graphql types that extend from the base type.

Every GraphQL Model on Mikro gets a identifier and shrinking methods to ensure the compatibliity
with arkitekt. This is done by adding the identifier and the shrinking methods to the graphql type.
If you want to add your own traits to the graphql type, you can do so by adding them in the graphql
.config.yaml file.

"""

from typing import Awaitable, List, TypeVar, Tuple, Protocol, Optional
import numpy as np
from pydantic import BaseModel
import xarray as xr
import pandas as pd
from rath.links.shrink import ShrinkByID
from typing import TYPE_CHECKING
from .scalars import FiveDVector
from .utils import get_attributes_or_error
from rath.scalars import ID
from typing import Any
import pyarrow.parquet as pq

if TYPE_CHECKING:
    pass


class Image(BaseModel):
    """Representation Trait

    Implements both identifier and shrinking methods.
    Also Implements the data attribute

    Attributes:
        data (xarray.Dataset): The data of the representation.

    """

    @property
    def data(self) -> xr.DataArray:
        store = get_attributes_or_error(self, "store")
        return xr.open_zarr(store=store.zarr_store, consolidated=True)["data"]

    async def adata(self) -> Awaitable[xr.DataArray]:
        """The Data of the Representation as an xr.DataArray. Accessible from asyncio.

        Returns:
            xr.DataArray: The associated object.

        Raises:
            AssertionError: If the representation has no store attribute quries
        """
        pstore = get_attributes_or_error(self, "store")
        return await pstore.aopen()

    def get_pixel_size(self, stage: ID = None) -> Tuple[float, float, float]:
        """The pixel size of the representation

        Returns:
            Tuple[float, float, float]: The pixel size
        """
        views = get_attributes_or_error(self, "views")

        for view in views:
            if isinstance(view, PixelTranslatable):
                if stage is None:
                    return view.pixel_size
                else:
                    if get_attributes_or_error(view, "stage.id") == stage:
                        return view.pixel_size

        raise NotImplementedError(
            f"No pixel size found for this representation {self}. Have you attached any views?"
        )



class Stage:
    pass


class Objective:
    """Additional Methods for ROI"""

    pass


class PhysicalSizeProtocol(Protocol):
    """A Protocol for Vectorizable data

    Attributes:
        x (float): The x value
        y (float): The y value
        z (float): The z value
        t (float): The t value
        c (float): The c value
    """

    x: float
    y: float
    z: float
    t: float
    c: float

    def __call__(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        z: Optional[int] = None,
        t: Optional[int] = None,
        c: Optional[int] = None,
    ):
        ...


class PhysicalSize:
    """Additional Methods for PhysicalSize"""

    def is_similar(
        self: PhysicalSizeProtocol,
        other: PhysicalSizeProtocol,
        tolerance: Optional[float]=0.02,
        raise_exception: Optional[bool]=False,
    ) -> bool:
        if hasattr(self, "x") and self.x is not None and other.x is not None:
            if abs(other.x - self.x) > tolerance:
                if raise_exception:
                    raise ValueError(
                        f"X values are not similar: {self.x} vs {other.x} is above tolerance {tolerance}"
                    )
                return False
        if hasattr(self, "y") and self.y is not None and other.y is not None:
            if abs(other.y - self.y) > tolerance:
                if raise_exception:
                    raise ValueError(
                        f"Y values are not similar: {self.y} vs {other.y} is above tolerance {tolerance}"
                    )
                return False
        if hasattr(self, "z") and self.z is not None and other.z is not None:
            if abs(other.z - self.z) > tolerance:
                if raise_exception:
                    raise ValueError(
                        f"Z values are not similar: {self.z} vs {other.z} is above tolerance {tolerance}"
                    )
                return False
        if hasattr(self, "t") and self.t is not None and other.t is not None:
            if abs(other.t - self.t) > tolerance:
                if raise_exception:
                    raise ValueError(
                        f"T values are not similar: {self.t} vs {other.t} is above tolerance {tolerance}"
                    )
                return False
        if hasattr(self, "c") and self.c is not None and other.c is not None:
            if abs(other.c - self.c) > tolerance:
                if raise_exception:
                    raise ValueError(
                        f"C values are not similar: {self.c} vs {other.c} is above tolerance {tolerance}"
                    )
                return False

        return True

    def to_scale(self):
        return [
            getattr(self, "t", 1),
            getattr(self, "c", 1),
            getattr(self, "z", 1),
            getattr(self, "y", 1),
            getattr(self, "x", 1),
        ]


class ROI(BaseModel):
    """Additional Methods for ROI"""

    @property
    def vector_data(self) -> np.ndarray:
        """A numpy array of the vectors of the ROI

        Returns:
            np.ndarray: _description_
        """
        return self.get_vector_data(dims="yx")

    def get_vector_data(self, dims="yx") -> np.ndarray:
        vector_list = getattr(self, "vectors", None)
        assert (
            vector_list
        ), "Please query 'vectors' in your request on 'ROI'. Data is not accessible otherwise"
        vector_list: list
        accesors = list(dims)
        return np.array([[getattr(v, ac) for ac in accesors] for v in vector_list])

    def center(self) -> FiveDVector:
        """The center of the ROI

        Caluclates the geometrical center of the ROI according to its type
        and the vectors of the ROI.

        Returns:
            InputVector: The center of the ROI
        """
        from mikro_next.api.schema import RoiTypeInput, InputVector

        assert hasattr(
            self, "type"
        ), "Please query 'type' in your request on 'ROI'. Center is not accessible otherwise"
        if self.type == RoiTypeInput.RECTANGLE:
            return InputVector.from_array(
                self.get_vector_data(dims="ctzyx").mean(axis=0)
            )

        raise NotImplementedError(
            f"Center calculation not implemented for this ROI type {self.type}"
        )

    def center_as_array(self) -> np.ndarray:
        """The center of the ROI

        Caluclates the geometrical center of the ROI according to its type
        and the vectors of the ROI.

        Returns:
            InputVector: The center of the ROI
        """
        from mikro_next.api.schema import RoiTypeInput

        assert hasattr(
            self, "type"
        ), "Please query 'type' in your request on 'ROI'. Center is not accessible otherwise"
        if self.type == RoiTypeInput.RECTANGLE:
            return self.get_vector_data(dims="ctzyx").mean(axis=0)
        if self.type == RoiTypeInput.POINT:
            return self.get_vector_data(dims="ctzyx")[0]

        raise NotImplementedError(
            f"Center calculation not implemented for this ROI type {self.type}"
        )


class Table(BaseModel, ShrinkByID):
    """Table Trait

    Implements both identifier and shrinking methods.
    Also Implements the data attribute

    Attributes:
        data (pd.DataFrame): The data of the table.

    """

    @property
    def data(self) -> pd.DataFrame:
        """The data of this table as a pandas dataframe

        Returns:
            pd.DataFrame: The Dataframe
        """
        store: "ParquetStore" = get_attributes_or_error(self, "store")
        return store.parquet_dataset.read_pandas().to_pandas()


class File(BaseModel, ShrinkByID):
    """Table Trait

    Implements both identifier and shrinking methods.
    Also Implements the data attribute

    Attributes:
        data (pd.DataFrame): The data of the table.

    """


V = TypeVar("V")


class ZarrStore(BaseModel):
    _openstore: Any = None

    @property
    def zarr_store(self):
        from mikro_next.io.download import open_zarr_store

        if self._openstore is None:
            id = get_attributes_or_error(self, "id")
            self._openstore = open_zarr_store(id)
        return self._openstore

    class Config:
        underscore_attrs_are_private = True


class ParquetStore(BaseModel):
    _dataset: Any = None

    @property
    def parquet_dataset(self) -> pq.ParquetDataset:
        from mikro_next.io.download import open_parquet_filesystem

        if self._dataset is None:
            id = get_attributes_or_error(self, "id")
            self._dataset = open_parquet_filesystem(id)
        return self._dataset

    class Config:
        underscore_attrs_are_private = True


class BigFileStore(BaseModel):
    _dataset: Any = None

    def download(self, file_name: str = None) -> pq.ParquetDataset:
        from mikro_next.io.download import download_bigfile

        id = get_attributes_or_error(self, "id")
        return download_bigfile(id, file_name=file_name)

    class Config:
        underscore_attrs_are_private = True


class MediaStore(BaseModel):
    _dataset: Any = None

    def download(self, file_name: str = None) -> pq.ParquetDataset:
        from mikro_next.io.download import download_file

        url, key = get_attributes_or_error(self, "presigned_url", "key")
        return download_file(url, file_name=file_name or key)

    class Config:
        underscore_attrs_are_private = True


class Vector(Protocol):
    """A Protocol for Vectorizable data

    Attributes:
        x (float): The x value
        y (float): The y value
        z (float): The z value
        t (float): The t value
        c (float): The c value
    """

    x: float
    y: float
    z: float
    t: float
    c: float

    def __call__(
        self: V,
        x: Optional[int] = None,
        y: Optional[int] = None,
        z: Optional[int] = None,
        t: Optional[int] = None,
        c: Optional[int] = None,
    ) -> V:
        ...


T = TypeVar("T", bound=Vector)


class PixelTranslatable:
    """Mixin for PixelTranslatable data"""

    @property
    def pixel_size(self) -> Tuple[float, float, float]:
        """The pixel size of the representation

        Returns:
            Tuple[float, float, float]: The pixel size
        """
        kind, matrix = get_attributes_or_error(self, "kind", "matrix")

        if kind == "AFFINE":
            return tuple(np.array(matrix).reshape(4, 4).diagonal()[:3])

        raise NotImplementedError(f"Pixel size not implemented for this kind {kind}")

    @property
    def position(self) -> Tuple[float, float, float]:
        """The pixel size of the representation

        Returns:
            Tuple[float, float, float]: The pixel size
        """
        kind, matrix = get_attributes_or_error(self, "kind", "matrix")

        if kind == "AFFINE":
            return tuple(np.array(matrix).reshape(4, 4)[:3, 3])

        raise NotImplementedError(f"Pixel size not implemented for this kind {kind}")


class Vectorizable:
    """Mixin for Vectorizable data
    adds functionality to convert a numpy array to a list of vectors
    """

    @classmethod
    def list_from_numpyarray(
        cls: T,
        x: np.ndarray,
        t: Optional[int] = None,
        c: Optional[int] = None,
        z: Optional[int] = None,
    ) -> List[T]:
        """Creates a list of InputVector from a numpya array

        Args:
            vector_list (List[List[float]]): A list of lists of floats

        Returns:
            List[Vectorizable]: A list of InputVector
        """
        assert x.ndim == 2, "Needs to be a List array of vectors"
        if x.shape[1] == 4:
            return [cls(x=i[1], y=i[0], z=i[2], t=i[3], c=c) for i in x.tolist()]
        if x.shape[1] == 3:
            return [cls(x=i[1], y=i[0], z=i[2], t=t, c=c) for i in x.tolist()]
        elif x.shape[1] == 2:
            return [cls(x=i[1], y=i[0], t=t, c=c, z=z) for i in x.tolist()]
        else:
            raise NotImplementedError(
                f"Incompatible shape {x.shape} of {x}. List dimension needs to either be of size 2 or 3"
            )

    @classmethod
    def from_array(
        cls: T,
        x: np.ndarray,
    ) -> T:
        return cls(x=x[4], y=x[3], z=x[2], t=x[1], c=x[0])
