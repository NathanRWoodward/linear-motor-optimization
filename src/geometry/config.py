class MagnetConfig:
    def __init__(self):
        self.length = 25.4
        """Depth of the U channel (Z)"""
        self.width = 6.35
        """Along the direction of motion (X)"""
        self.thickness = 6.35
        """Thickness of the magnet (Y)"""
        self.debug_labels = False
        """Whether to add labels to the magnet faces for debugging"""


class HalbachConfig(MagnetConfig):
    def __init__(self):
        super().__init__()
        self.count = 8
        """Total number of magnets in the array"""


class DualHalbachConfig(HalbachConfig):
    def __init__(self):
        super().__init__()
        self.gap = 5
        """Gap between the two arrays (Y)"""
