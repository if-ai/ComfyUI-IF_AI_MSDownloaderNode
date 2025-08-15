import os
import importlib.util
import glob
import shutil
from .IFHFDownloadNode import IFHFDownload 
from .IFMSDownloadNode import IFMSDownload

NODE_CLASS_MAPPINGS = {
    "IF_HFDownload": IFHFDownload,
    "IF_MSDownload": IFMSDownload,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "IF_HFDownload": "Hugging Face Download🤗",
    "IF_MSDownload": "ModelScope Download🧩",
}

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
