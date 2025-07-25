from pydantic import BaseModel
import numpy as np
import xarray as xr
from mikro_next.scalars import ArrayLike


class Arguments(BaseModel):
    """Arguments for testing serialization of numpy and xarray arrays."""

    x: ArrayLike


def test_numpy_serialization() -> None:
    """Test that numpy arrays are serialized correctly."""
    x = np.random.random((20, 1000, 1000))

    t = Arguments(x=x)
    assert t.x.value.ndim == 5, "Should be five dimensionsal"


def test_xarray_serialization() -> None:
    """Test that xarray arrays are serialized correctly."""
    x = xr.DataArray(np.zeros((1000, 1000, 10)), dims=["x", "y", "z"])

    t = Arguments(x=x)
    assert t.x.value.ndim == 5, "Should be five dimensionsal"
