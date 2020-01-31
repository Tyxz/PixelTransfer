#!/usr/bin/python

from PIL import Image, ImageChops, ImageColor, ImageEnhance
import collections
import os
import glob
import errno
from pathlib import Path


class Transfer(object):
    """Transfer object to transfer pixel information from one image to another.
    
    :param base_path: path to the base image or folder
    :type base_path: str
    :param goal_path: path to the goal image or folder
    :type goal_path: str
    :param base_filter: filter to be used on the base image, defaults to "*"
    :type base_filter: str, optional
    :param goal_filter: filter to be used on the goal image, defaults to "*"
    :type goal_filter: str, optional
    :param exclude: list of names to be excluded from the input, defaults to []
    :type exclude: list, optional
    :param include: list of names to be included by the input, defaults to []
    :type include: list, optional
    :param out_path: path where the result should be stored, defaults to "out"
    :type out_path: str, optional
    :param size: size tuple [width, height] if you want the result to be resized, defaults to None
    :type size: [int], optional
    :param verbose: if you want a output to the console, defaults to True
    :type verbose: bool, optional
    :param tint: if you want to tint the image, defaults to False
    :type tint: bool, optional
    :param colour: Specific colour of the tint. If not given but tint is true, the majority colour of the image will be used, defaults to None
    :type colour: str, optional
    :param merge: percentage [0-100] of merging the goal image into the base, defaults to 0
    :type merge: int, optional
    :param brightness: enhancement factor for the brightness: 0.0 is black, 1.0 is normal and > 1.0 is brighter, defaults to 1.0
    :type brightness: float, optional
    :param contrast: enhancement factor for the contrast: 0.0 is grey, 1.0 is normal and > 1.0 is more contrast, defaults to 1.0
    :type contrast: float, optional
    :param sharpness: enhancement factor for the sharpness: 0.0 is smooth, 1.0 is normal and > 1.0 is sharper, defaults to 1.0
    :type sharpness: float, optional
    :param tint_threshold: threshold for the alpha value (0-255) to calculate the majority colour., defaults to 100
    :type tint_threshold: int, optional
    """
    def __get_colors_by_frequency(self, value: object) -> object:
        return collections.Counter([value[i, j] for i in range(self.width) for j in range(self.height) if value[i, j][3] >= self.tint_threshold])

    def __getTint(self, value: object) -> tuple:
        colors = self.__get_colors_by_frequency(value)
        return colors.most_common(1)[0][0]

    def __tint_image(self, dest: object, goal: object, colour=None) -> object:
        tint_color = ()
        if colour is None:
            pixel_values = goal.load()
            tint_color = self.__getTint(pixel_values)
        else:
            tint_color = ImageColor.getrgb(colour)

        return ImageChops.multiply(dest, Image.new('RGBA', dest.size, tint_color))

    def __imageInformations(self, path: Path) -> (object, int, int, object):
        image = Image.open(path, 'r')
        width, height = image.size
        pixel_values = image.load()
        return image, width, height, pixel_values

    def __outName(self, image_path: Path, out_path: str, width: int = None, height: int = None) -> str:
        name = os.path.basename(image_path).split('.')[0]
        if height and width:
            name += f"_{width}x{height}"
        return os.path.join(out_path, name)

    def __create_dirs(self, out_path: str) -> None:
        try:
            os.makedirs(out_path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(out_path):
                pass
            else:
                raise

    def __alpha_transfer(self, base_values: object, goal_values: object) -> object:
        destination_image = Image.new('RGBA', (self.width, self.height))
        destination_values = destination_image.load()

        for i in range(self.width):
            for j in range(self.height):
                base = list(base_values[i, j])
                goal = goal_values[i, j]
                alpha = goal[3]
                merge = self.merge
                base.append(alpha)
                if merge > 0:
                    for k in range(len(base)):
                        base[k] = int(
                            (goal[k] * merge + base[k] * (100-merge)) / 100)
                destination_values[i, j] = tuple(base)

        return destination_image

    def __resizeImage(self, image: object, size: tuple) -> object:
        assert len(
            size) == 2, f"size needs be a tuple (width, height) not {size}"
        return image.resize(size, Image.ANTIALIAS)

    def __saveImage(self, goal_image_path: Path, destination_image: object, out_path: str) -> None:
        out = self.__outName(goal_image_path, out_path,
                             self.width, self.height)
        out = f"{out}.png"
        if self.verbose:
            print(f"Save to {out}")
        destination_image.save(out)

    def createImage(self, base_image_path: Path, goal_image_path: Path, out_path="out") -> None:
        """Create an pixel transfer image.
        
        :param base_image_path: path to the base image
        :type base_image_path: Path
        :param goal_image_path: path to the goal image
        :type goal_image_path: Path
        :param out_path: path where the result will be saved, defaults to "out"
        :type out_path: str, optional
        :raises TypeError: if base image is not RGB or RGBA
        :raises TypeError: if goal image is not RGBA
        """
        self.__create_dirs(out_path)

        base_image, base_width, base_height, base_values = self.__imageInformations(
            base_image_path)
        goal_image, goal_width, goal_height, goal_values = self.__imageInformations(
            goal_image_path)

        if base_image.mode not in ['RGB', 'RGBA']:
            raise TypeError(f'Unsupported base image mode: {base_image.mode}')
        if goal_image.mode not in ['RGBA']:
            raise TypeError(f'Unsupported goal image mode: {goal_image.mode}')

        self.height, self.width = base_height, base_width

        if goal_height != base_height or goal_width != base_width:
            goal_image = self.__resizeImage(
                goal_image, (self.width, self.height))

        destination_image = self.__alpha_transfer(base_values, goal_values)

        if self.tint:
            destination_image = self.__tint_image(
                destination_image, goal_image, self.colour)

        destination_image = ImageEnhance.Brightness(
            destination_image).enhance(self.brightness)

        destination_image = ImageEnhance.Contrast(
            destination_image).enhance(self.contrast)

        destination_image = ImageEnhance.Sharpness(
            destination_image).enhance(self.sharpness)

        if self.size is not None:
            self.width, self.height = self.size
            destination_image = self.__resizeImage(
                destination_image, self.size)

        self.__saveImage(goal_image_path, destination_image, out_path)

    def __SkipImage(self, image: Path):
        for e in self.exclude:
            print(image, e)
            if e in str(image):
                return True
        isNotIncluded = len(self.include) != 0
        for i in self.include:
            if i in str(image):
                isNotIncluded = False
                break
        return isNotIncluded

    def __setupGoal(self, base_image: str, out_path: str):
        if os.path.isdir(self.goal):
            for goal_image in Path(self.goal).rglob(self.goal_filter):
                if self.__SkipImage(goal_image):
                    continue
                if self.verbose:
                    print(goal_image)
                self.createImage(base_image, goal_image, out_path)
        elif os.path.isfile(self.goal):
            self.createImage(base_image, self.goal, out_path)

    def run(self):
        """Run the transfer module with the previous given values.
        """
        if os.path.isdir(self.base):
            for base_image in Path(self.base).rglob(self.base_filter):
                if self.__SkipImage(base_image):
                    continue
                out_path = self.__outName(base_image, self.out_path)
                if self.verbose:
                    print(base_image)
                self.__setupGoal(base_image, out_path)
        elif os.path.isfile(self.base):
            out_path = self.__outName(self.base, self.out_path)
            self.__setupGoal(self.base, out_path)

    def __init__(self, base_path: str, goal_path: str,
                 base_filter="*", goal_filter="*", exclude=[], include=[], out_path="out", size=None,
                 verbose=True, tint=False, colour=None, merge=0, brightness=1.0, contrast=1.0, sharpness=1.0, tint_threshold=100):
        assert colour is not None and tint or colour is None, "Colour will only be working if tint is enabled"
        assert tint_threshold <= 255, "Threshold is too big"
        assert brightness >= 0.0, "Brightness is to small"
        assert merge >= 0, "Merge must be positive"
        assert size is None or len(
            size) == 2, "Size needs to be a tuple of 2 values: (width, height)"
        self.base = base_path
        self.goal = goal_path
        self.goal_filter = goal_filter
        self.base_filter = base_filter
        self.out_path = out_path
        self.exclude = exclude
        self.include = include
        self.verbose = verbose
        self.size = size
        self.tint = tint
        self.colour = colour
        self.merge = merge
        self.brightness = brightness
        self.contrast = contrast
        self.sharpness = sharpness
        self. tint_threshold = tint_threshold


def get_parser() -> object:
    import argparse

    def check_100(value: int):
        ivalue = int(value)
        if ivalue < 0 or ivalue > 100:
            raise argparse.ArgumentTypeError(
                f"{value} is an invalid percentage int value")
        return ivalue

    parser = argparse.ArgumentParser(
        description='Python script to transfer alpha values from one image (goal) to another (base).\nAdditionally, you can also tint the base image based on the majority colour of the goal image, or merge the two together.')
    parser.add_argument('base', help="Image you want to see edited.")
    parser.add_argument(
        'goal', help="Image you want to take the alpha value and tint from.")
    ag0 = parser.add_argument_group(
        'Filter the source images in a folder.')
    ag0.add_argument('-bf', '--base_filter', default="*",
                        help="Filter the base image folder.")
    ag0.add_argument('-gf', '--goal_filter', default="*",
                        help="Filter the goal image folder.")
    e1 = ag0.add_mutually_exclusive_group(required=False)
    e1.add_argument('-e', '--exclude', nargs='*', default=[],
                    help="Exclude a list of file names.")
    e1.add_argument('-i', '--include', nargs='*', default=[],
                    help="Include only a list file names.")
    parser.add_argument('-o', '--out', default="out",
                        help="Base directory where the output is saved.")
    parser.add_argument('-s', '--size', nargs='+', default=None,
                        type=int, help="Width and height of the resulting image.")
    parser.add_argument('-m', '--merge', type=check_100,
                        help="Merge with goal in percent from 0-100.", default=0)
    parser.add_argument('-v', '--verbose', action='store_true', default=False)
    ag1 = parser.add_argument_group(
        'Enhance various aspects of the image.')
    ag1.add_argument('-b', '--brightness',
                     help="Improve brightness with an value between 0.0 and infty. 0.0 is black, 1.0 is normal and everything above is brighter.", type=float, default=1.0)
    ag1.add_argument('-ct', '--contrast',
                     help="Improve contrast with an value between 0.0 and infty.", type=float, default=1.0)
    ag1.add_argument('-sh', '--sharpness',
                     help="Improve sharpness with an value between 0.0 and infty.", type=float, default=1.0)
    ag2 = parser.add_argument_group(
        'Tint the base images with the majority colour of the goal image or a given colour.')
    ag2.add_argument('-t', '--tint', help="Add tint from the goal image.",
                     action='store_true', default=False)
    ag2.add_argument('-c', '--colour', help="Specify a colour.")

    return parser




if __name__ == "__main__":

    parser = get_parser()
    args = parser.parse_args()

    out_path = os.path.join(args.out, "")
    needSeparator = False
    
    def __add_to_name(name: str, value: str, needSeparator: bool, out_path: str) -> (bool, str):
        if needSeparator:
            out_path += "_"
        out_path += f"{name}{value}"
        return True, out_path

    if args.tint:
        out_path += "t"
        if args.colour is not None:
            out_path += f"_{args.colour}"
        needSeparator = True
    if args.brightness != 1.0:
        needSeparator, out_path = __add_to_name("b", args.brightness, needSeparator, out_path)
    if args.contrast != 1.0:
        needSeparator, out_path = __add_to_name("c", args.contrast, needSeparator, out_path)
    if args.sharpness != 1.0:
        needSeparator, out_path = __add_to_name("s", args.sharpness, needSeparator, out_path)
    if args.merge > 0:
        needSeparator, out_path = __add_to_name("m", args.merge, needSeparator, out_path)

    if args.verbose:
        print(out_path)

    transfer = Transfer(args.base, args.goal, args.base_filter, args.goal_filter, args.exclude,
                        args.include, out_path, args.size, args.verbose, args.tint, args.colour, args.merge, args.brightness, args.contrast, args.sharpness)
    transfer.run()
