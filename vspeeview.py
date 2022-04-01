import numpy as np
import sys
import cms

from texturegl import TextureGL

from PySide2 import QtWidgets

from PySide2.QtWidgets import QApplication
from PySide2.QtWidgets import QSlider

from PySide2.QtCore import Qt

import vapoursynth as vs

from vsengine.policy import Policy, GlobalStore
import vsengine.vpy as vpy
import vsengine.video as video


class GLWindow(QtWidgets.QMainWindow):

    def __init__(self, script, parent=None):
        super().__init__(parent)

        self.app = QApplication.instance()

        self.mainwidget = QtWidgets.QWidget()
        parent_layout = QtWidgets.QHBoxLayout()
        self.mainwidget.setLayout(parent_layout)

        self.setCentralWidget(self.mainwidget)
        self.setWindowTitle("vspeeview")
        self.setMinimumSize(800, 600)

        main_section = QtWidgets.QWidget()
        parent_layout.addWidget(main_section)

        layout = QtWidgets.QVBoxLayout()
        main_section.setLayout(layout)

        self.glwidget = TextureGL()
        layout.addWidget(self.glwidget)

        self.luts = cms.load_3dluts(self.app, 65)

        self.glwidget.update_3dlut(self.luts[1])

        slider = QSlider(orientation=Qt.Orientation.Horizontal)
        layout.addWidget(slider)

        with Policy(GlobalStore()) as p:
            with p.new_environment() as env:
                vpy.script(script, env.vs_environment).result()

                self.videonode = env.outputs[0].clip

        slider.setMaximum(self.videonode.num_frames - 1)
        slider.setTickInterval(1)
        slider.valueChanged.connect(self.slider_changed)

        self.resolutions = [(p.width, p.height)
                            for p in self.videonode.std.SplitPlanes()]
        self.bit_depth = self.videonode.format.bits_per_sample
        self.sample_type = self.videonode.format.sample_type

        self.render_frame(0)

    def slider_changed(self, n):
        self.render_frame(n)

    def render_frame(self, n):
        planes = video.planes(self.videonode, n, [0, 1, 2]).result()

        planes = [np.frombuffer(plane, dtype=np.uint16) for plane in planes]
        self.glwidget.update_image(planes, self.resolutions, 0, 0,
                                   self.bit_depth, self.sample_type)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_A:
            import random
            frame = random.randint(0, self.videonode.num_frames - 1)
            self.render_frame(frame)
        elif event.key() == Qt.Key_Z:
            self.glwidget.update_3dlut(self.glwidget.lut_identity)
        elif event.key() == Qt.Key_X:
            self.glwidget.update_3dlut(
              self.luts[self.app.desktop().screenNumber(self)])
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    app = QtWidgets.QApplication()
    window = GLWindow(sys.argv[1])
    window.show()
    res = app.exec_()
    sys.exit(res)
