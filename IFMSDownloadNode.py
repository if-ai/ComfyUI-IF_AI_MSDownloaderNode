import os
import math
import re
import shutil
import subprocess
from aiohttp import web
from dotenv import load_dotenv
from comfy.utils import ProgressBar
from server import PromptServer
from modelscope import snapshot_download as ms_snapshot_download


class ComfyProgress:
    def __init__(self, total):
        self.progress = ProgressBar(total)
        self.total_size = total

    def update(self, n=1, text: str | None = None):
        self.progress.update(n)
        current = self.progress.current
        message = text if text else f"Progress: {current}/{self.total_size}"
        PromptServer.instance.send_sync("progress", {
            "value": current,
            "max": self.total_size,
            "text": message
        })

    @staticmethod
    def format_bytes(size):
        if size <= 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size, 1024)))
        p = math.pow(1024, i)
        s = round(size / p, 2)
        return f"{s} {size_name[i]}"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class IFMSDownload:
    def __init__(self):
        self.output = None
        self.comfy_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.download_dir = os.path.join(self.comfy_dir, "models")
        load_dotenv(os.path.join(self.comfy_dir, '.env'))

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_id": ("STRING", {"multiline": False}),
                "file_paths": ("STRING", {"multiline": True, "default": "comma-separated list of files or leave empty for all"}),
                "folder_path": ("STRING", {"multiline": False, "default": "/path/to/download/folder"}),
                "comfy_paths": ([
                    "none", "animatediff_models", "animatediff_motion_lora", "animatediff_video_formats",
                    "blip", "checkpoints", "classifiers", "clip", "clip_vision", "CogVideo", "configs", "controlnet", "control-lora",
                    "deforum", "diffusers", "diffusion_models", "embeddings", "emotion2vec", "facedetection",
                    "FILM", "gligen", "hypernetworks", "insightface",
                    "Joy_caption", "layerstyle", "liveportrait",  "LLM", "loras", "onnx", "photomaker", "style_models",
                    "unet", "upscale_models", "vae", "vae_approx", "wav2vec", "xlabs"
                ], {"default": "none"}),
                "exclude_files": ("STRING", {"multiline": True, "default": "comma-separated list to exclude"}),
            },
            "optional": {
                "mode": ("BOOLEAN", {"default": False, "label_on": "Full Model", "label_off": "Individual Files"}),
                "provided_token": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "download_ms"
    CATEGORY = "ImpactFrames💥🎞️/utils"

    def get_ms_token(self, provided_token=None):
        # Priority: provided token -> env var -> None (public models)
        token = None
        if provided_token is not None and provided_token != "":
            token = provided_token
        elif os.getenv("MODELSCOPE_API_TOKEN"):
            token = os.getenv("MODELSCOPE_API_TOKEN")

        if token:
            os.environ["MODELSCOPE_API_TOKEN"] = token
        return token

    def get_safe_folder_name(self, model_id):
        folder_name = model_id.split('/')[-1]
        safe_name = re.sub(r'[^\w\-_\. ]', '_', folder_name)
        return safe_name

    def resolve_download_folder(self, comfy_paths, folder_path):
        if folder_path and folder_path != "/path/to/download/folder" and os.path.isdir(folder_path):
            return folder_path
        if comfy_paths != "none":
            return os.path.join(self.download_dir, comfy_paths)
        return os.path.join(self.download_dir, "IF_AI")

    def download_ms(self, mode, model_id, file_paths, comfy_paths, folder_path, exclude_files, provided_token=None):
        try:
            self.get_ms_token(provided_token)
        except Exception as e:
            self.output = str(e)
            return (self.output,)

        exclude_list = [f.strip() for f in exclude_files.split(",") if f.strip()]

        download_folder = self.resolve_download_folder(comfy_paths, folder_path)
        model_folder_name = self.get_safe_folder_name(model_id)
        model_download_folder = os.path.join(download_folder, model_folder_name)
        os.makedirs(model_download_folder, exist_ok=True)

        if mode:
            # Full model snapshot via SDK
            try:
                with ComfyProgress(1) as pbar:
                    pbar.update(0, text=f"Downloading model snapshot: {model_id}")
                    ms_snapshot_download(model_id, cache_dir=model_download_folder)
                    pbar.update(1, text="Download complete")
                # post-clean excluded
                self._remove_excluded_files(model_download_folder, exclude_list)
                self.output = f"Downloaded model: {model_id} to {model_download_folder}"
            except Exception as e:
                self.output = f"Error downloading model: {str(e)}"
                print(f"ModelScope snapshot_download error: {str(e)}")
        else:
            # Individual files via CLI (modelscope)
            files = [f.strip() for f in file_paths.split(',') if f.strip()]
            if not files:
                self.output = "No files specified. Provide file_paths or enable Full Model mode."
                return (self.output,)

            cli_path = shutil.which("modelscope")
            if not cli_path:
                self.output = "modelscope CLI not found. Install with: pip install modelscope"
                return (self.output,)

            with ComfyProgress(len(files)) as pbar:
                for idx, file in enumerate(files, start=1):
                    if file in exclude_list:
                        pbar.update(1, text=f"Skipping excluded file {idx}/{len(files)}: {file}")
                        continue
                    try:
                        pbar.update(0, text=f"Downloading file {idx}/{len(files)}: {file}")
                        cmd = [cli_path, "download", "--model", model_id, file, "--local_dir", model_download_folder]
                        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        pbar.update(1, text=f"Downloaded {file}")
                    except subprocess.CalledProcessError as e:
                        err = e.stderr.decode(errors='ignore') if e.stderr else str(e)
                        print(f"Error downloading {file}: {err}")
                    except Exception as e:
                        print(f"Unexpected error downloading {file}: {str(e)}")

            self.output = f"Downloaded selected files from {model_id} to {model_download_folder}"

        return (self.output,)

    def _remove_excluded_files(self, root_folder: str, exclude_list: list[str]):
        if not exclude_list:
            return
        for root, _, files in os.walk(root_folder):
            for f in files:
                rel_path = os.path.relpath(os.path.join(root, f), root_folder)
                if rel_path in exclude_list:
                    try:
                        os.remove(os.path.join(root, f))
                    except Exception:
                        pass


NODE_CLASS_MAPPINGS = {"IF_MSDownload": IFMSDownload}
NODE_DISPLAY_NAME_MAPPINGS = {"IF_MSDownload": "ModelScope Download🧩"}


