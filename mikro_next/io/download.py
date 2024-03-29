from mikro_next.api.schema import (
    arequest_access,
    arequest_table_access,
    arequest_file_access,
    AccessCredentialsFragment,
)
from mikro_next.datalayer import current_next_datalayer
import s3fs
import pyarrow.parquet as pq
from koil import unkoil
import zarr
import aiohttp
from typing import Tuple, Optional


async def aget_zarr_credentials_and_endpoint(
    store: str,
) -> Tuple[AccessCredentialsFragment, str]:
    credentials = await arequest_access(store)
    endpoint_url = await current_next_datalayer.get().get_endpoint_url()
    return credentials, endpoint_url


async def aget_table_credentials_and_endpoint(store):
    credentials = await arequest_table_access(store)
    endpoint_url = await current_next_datalayer.get().get_endpoint_url()
    return credentials, endpoint_url


async def aget_file_credentials_and_endpoint(store):
    credentials = await arequest_file_access(store)
    endpoint_url = await current_next_datalayer.get().get_endpoint_url()
    return credentials, endpoint_url


async def aopen_zarr_store(store_id: str, cache: int = 2**30):
    credentials, endpoint_url = await aget_zarr_credentials_and_endpoint(store_id)

    _s3fs = s3fs.S3FileSystem(
        secret=credentials.secret_key,
        key=credentials.access_key,
        client_kwargs={
            "endpoint_url": endpoint_url,
            "aws_session_token": credentials.session_token,
        },
        asynchronous=True,
    )

    return zarr.LRUStoreCache(_s3fs.get_mapper(credentials.path), cache)


def open_zarr_store(store_id: str, cache: int = 2**30):
    credentials, endpoint_url = unkoil(aget_zarr_credentials_and_endpoint, store_id)

    _s3fs = s3fs.S3FileSystem(
        secret=credentials.secret_key,
        key=credentials.access_key,
        client_kwargs={
            "endpoint_url": endpoint_url,
            "aws_session_token": credentials.session_token,
        },
        asynchronous=False,
    )

    return zarr.LRUStoreCache(_s3fs.get_mapper(credentials.path), cache)


async def aopen_parquet_filesytem(store_id: str):
    credentials, endpoint_url = await aget_table_credentials_and_endpoint(store_id)

    _s3fs = s3fs.S3FileSystem(
        secret=credentials.secret_key,
        key=credentials.access_key,
        client_kwargs={
            "endpoint_url": endpoint_url,
            "aws_session_token": credentials.session_token,
        },
        asynchronous=True,
    )

    return pq.ParquetDataset(credentials.path, filesystem=_s3fs)


def open_parquet_filesystem(store_id: str):
    credentials, endpoint_url = unkoil(aget_table_credentials_and_endpoint, store_id)

    _s3fs = s3fs.S3FileSystem(
        secret=credentials.secret_key,
        key=credentials.access_key,
        client_kwargs={
            "endpoint_url": endpoint_url,
            "aws_session_token": credentials.session_token,
        },
        asynchronous=False,
    )

    return pq.ParquetDataset(credentials.path, filesystem=_s3fs)


async def adownload_file(presigned_url: str, file_name: Optional[str] = None, datalayer=None):
    datalayer = datalayer or current_next_datalayer.get()
    endpoint_url = await datalayer.get_endpoint_url()

    async with aiohttp.ClientSession() as session:
        async with session.get(endpoint_url + presigned_url) as response:
            with open(file_name, "wb") as file:
                while True:
                    chunk = await response.content.read(
                        1024
                    )  # read the response by chunks of 1024 bytes
                    if not chunk:
                        break
                    file.write(chunk)

    return file_name


def download_file(presigned_url: str, file_name: Optional[str] = None, datalayer=None):
    return unkoil(
        adownload_file, presigned_url, file_name=file_name, datalayer=datalayer
    )
