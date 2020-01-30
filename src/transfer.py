from PIL import Image, ImageChops, ImageColor, ImageEnhance
import numpy as np
import argparse
import collections
import os  
import glob
import errno    

class Transfer:
    width = 0
    height = 0
    tint_threshold = 100
    tint = False
    colour = None
    merge = 0
    brightness = 1.0
    destination = None
    base = ""
    goal = ""
    base_filter = "*"
    goal_filter = "*"
    out_path = ""
    verbose = True
    exclude = []
    include = []



    def __get_colors_by_frequency(self, value):
        return collections.Counter([value[i,j] for i in range(self.width) for j in range(self.height) if value[i,j][3] >= self.tint_threshold])

    def __getTint(self, value):
        colors = self.__get_colors_by_frequency(value)
        return colors.most_common(1)[0][0]

    def __tint_image(self, dest, goal, colour = None):
        tint_color = ()
        if colour is None:
            pixel_values = goal.load()
            tint_color = self.__getTint(pixel_values)
        else:
            tint_color = ImageColor.getrgb(colour)

        return ImageChops.multiply(dest, Image.new('RGBA', dest.size, tint_color))

    def __imageInformations(self, path):
        image = Image.open(path, 'r')
        width, height = image.size
        pixel_values = image.load()
        return image, width, height, pixel_values

    def __outName(self, image_path, out_path):
        name = os.path.basename(image_path).split('.')[0]
        return os.path.join(out_path,name)

    def createImage(self, base_image_path, goal_image_path, out_path = "out"):
        try:
            os.makedirs(out_path)
        except OSError as exc: 
            if exc.errno == errno.EEXIST and os.path.isdir(out_path):
                pass
            else:
                raise
        
        base_image, base_width, base_height, base_values = self.__imageInformations(base_image_path)
        goal_image, goal_width, goal_height, goal_values = self.__imageInformations(goal_image_path)

        assert base_height == goal_height, "Base and goal image need to have the same height"
        assert base_width == goal_width, "Base and goal image need to have the same height"
        #assert len(goal_values[0,0]) == 4, "Goal image needs to have an alpha pixel"

        if base_image.mode not in ['RGB', 'RGBA']:
            raise TypeError(f'Unsupported base image mode: {base_image.mode}')
        if goal_image.mode not in ['RGBA']:
            raise TypeError(f'Unsupported goal image mode: {goal_image.mode}')

        self.height, self.width = base_height, base_width
        destination_image = Image.new('RGBA', (self.width, self.height))
        destination_values = destination_image.load()

        for i in range(self.width):
            for j in range(self.height):
                base = list(base_values[i,j])
                goal = goal_values[i,j]
                alpha = goal[3]
                merge = self.merge
                base.append(alpha)
                if merge > 0:
                    for k in range(len(base)):
                        base[k] = int((goal[k] * merge + base[k] * (100-merge)) / 100)
                destination_values[i,j] = tuple(base)

        if self.tint:
            destination_image = self.__tint_image(destination_image, goal_image, self.colour)

        destination_image = ImageEnhance.Brightness(destination_image).enhance(self.brightness)

        out = self.__outName(goal_image_path, out_path)
        out = f"{out}.png"
        if self.verbose:
            print(f"Save to {out}")
        destination_image.save(out)
        
    def __SkipImage(self, image):
        for e in self.exclude:
            if e in image:
                return True
        isNotIncluded = len(self.include) != 0
        for i in self.include:
            if i in image:
                isNotIncluded = False
                break
        return isNotIncluded

    def __setupGoal(self, base_image, out_path):
        if os.path.isdir(self.goal):
            for goal_image in glob.glob(os.path.join(self.goal,self.goal_filter)):
                if self.__SkipImage(goal_image):
                    continue
                if self.verbose:
                    print(goal_image)
                self.createImage(base_image, goal_image, out_path)
        elif os.path.isfile(self.goal):
            self.createImage(base_image, self.goal, out_path)

    def setupBase(self):
        if os.path.isdir(self.base):
            for base_image in glob.glob(os.path.join(self.base,self.base_filter)):
                if self.__SkipImage(base_image):
                    continue
                out_path = self.__outName(base_image, self.out_path)
                if self.verbose:
                    print(base_image)
                self.__setupGoal(base_image, out_path)
        elif os.path.isfile(self.base):
            out_path = self.__outName(self.base, self.out_path)
            self.__setupGoal(self.base, out_path)

    def __init__(self, base_path, goal_path, base_filter="*", goal_filter="*", exclude=[], include=[], out_path="out", verbose=True, tint=False, colour=None, merge=0, brightness=1.0, tint_threshold=100):
        assert tint_threshold <= 255, "Threshold is too big"
        assert brightness >= 0.0, "Brightness is to small"
        assert merge >= 0, "Merge must be positive"
        self.base = base_path
        self.goal = goal_path
        self.goal_filter = goal_filter
        self.base_filter = base_filter
        self.out_path = out_path
        self.exclude = exclude
        self.include = include
        self.verbose = verbose
        self.tint = tint
        self.colour = colour
        self.merge = merge
        self.brightness = brightness
        self. tint_threshold = tint_threshold


if __name__ == "__main__":
    def check_100(value):
        ivalue = int(value)
        if ivalue < 0 or ivalue > 100:
            raise argparse.ArgumentTypeError(f"{value} is an invalid percentage int value")
        return ivalue

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('base')
    parser.add_argument('goal')
    parser.add_argument('-bf', '--base_filter', default="*")
    parser.add_argument('-gf', '--goal_filter', default="*")
    a2 = parser.add_mutually_exclusive_group(required=False)
    a2.add_argument('-e', '--exclude', nargs='*', default=[])
    a2.add_argument('-i', '--include', nargs='*', default=[])
    parser.add_argument('-m', '--merge', type=check_100, help="Merge with goal in percent from 0-100", default=0)
    parser.add_argument('-b', '--brightness', help="Improve brightness", type=float, default=1.0)
    parser.add_argument('-v', '--verbose', action='store_true', default=False )
    ag1 = parser.add_argument_group('tint')
    ag1.add_argument('-t', '--tint', help="Add tint from goal", action='store_true', default=False )
    ag1.add_argument('-c', '--colour', help="Specify a colour" )
    args = parser.parse_args()

    out_path = os.path.join("out","")
    if args.tint:
        out_path += "t"
        if args.colour is not None:
            out_path += f"_{args.colour}"
    if args.brightness != 1.0:
        if args.tint:
            out_path += "_"
        out_path += f"b{args.brightness}"
    if args.merge > 0:
        if args.tint or args.brightness != 1.0:
            out_path += "_"
        out_path += f"m{args.merge}"
        
    if args.verbose:
        print(out_path)

    transfer = Transfer(args.base, args.goal, args.base_filter, args.goal_filter, args.exclude, args.include, out_path, args.verbose, args.tint, args.colour, args.merge, args.brightness)
    transfer.setupBase()