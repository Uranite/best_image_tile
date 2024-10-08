import os
import numpy as np
from pepeline import read, save, cvt_color, CvtType, best_tile, ImgColor, ImgFormat
import cv2
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from tqdm.contrib.concurrent import process_map, thread_map
from chainner_ext import resize, ResizeFilter

class BestTile:
    """
    Class for processing images to find and save the best tile with the highest Laplacian intensity.

    Attributes:
    - `in_folder` (str): Input folder containing images.
    - `out_folder` (str): Output folder to save processed images.
    - `tile_size` (int): Size of the tile to extract. Default is 1024.
    - `process_type` (str): Type of processing ('thread', 'process', or 'sequential'). Default is 'thread'.
    - `all_images` (list): List of all image filenames in the input folder.

    Methods:
    - `process(img_name: str)`: Process a single image to find and save the best tile.
    - `run()`: Run the processing on all images using the specified processing type.
    """

    def __init__(self, in_folder: str, out_folder: str, tile_size: int = 512, process_type: str = "sequential",
                 scale: int = 1):
        """
        Initialize the BestTile class.

        Args:
        - `in_folder` (str): Input folder containing images.
        - `out_folder` (str): Output folder to save processed images.
        - `tile_size` (int): Size of the tile to extract. Default is 512.
        - `process_type` (str): Type of processing ('thread', 'process', or 'for'). Default is 'thread'.
        """
        self.scale = scale
        self.in_folder = in_folder
        self.out_folder = out_folder
        if not os.path.exists(out_folder):
            os.makedirs(out_folder)
        self.tile_size = tile_size
        self.all_images = os.listdir(in_folder)
        self.process_type = process_type

    def process(self, img_name: str):
        """
        Process a single image to find and save the best tile.

        Args:
        - `img_name` (str): Name of the image file to process.
        """
        img = read(os.path.join(self.in_folder, img_name), ImgColor.RGB, ImgFormat.F32)
        img_shape = img.shape
        if img_shape[0] < self.tile_size or img_shape[1] < self.tile_size:
            return
        if img_shape[0] == self.tile_size or img_shape[1] == self.tile_size:
            save(img, os.path.join(self.out_folder, img_name))
            return
        result_name = ".".join(img_name.split(".")[:-1]) + ".png"
        img_gray = cvt_color(img, CvtType.RGB2GrayBt2020)
        laplacian_abs = np.abs(cv2.Laplacian(img_gray, -1))
        if self.scale > 1:
            laplacian_abs = resize(laplacian_abs, (img_shape[1] // self.scale, img_shape[0] // self.scale),
                                   ResizeFilter.Box, False).squeeze()
            left_up_cord = best_tile(laplacian_abs, self.tile_size // self.scale) * self.scale
        else:
            left_up_cord = best_tile(laplacian_abs, self.tile_size // self.scale)
        save(img[left_up_cord[0]:left_up_cord[0] + self.tile_size, left_up_cord[1]:left_up_cord[1] + self.tile_size],
             os.path.join(self.out_folder, result_name))

    def run(self):
        """
        Run the processing on all images using the specified processing type.
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(complete_style="green"),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            "ETA:",
            TimeRemainingColumn(),
            MofNCompleteColumn()
        ) as progress:
            task = progress.add_task("Processing images", total=len(self.all_images))

            def update_and_process(img_name: str):
                self.process(img_name)
                progress.advance(task)

            if self.process_type == "thread":
                thread_map(update_and_process, self.all_images)
            elif self.process_type == "process":
                process_map(update_and_process, self.all_images)
            else:
                for img_name in self.all_images:
                    update_and_process(img_name)
