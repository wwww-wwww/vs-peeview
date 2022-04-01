import cms

from PySide2.QtGui import QOpenGLShaderProgram
from PySide2.QtGui import QOpenGLShader
from PySide2.QtGui import QOpenGLContext

from PySide2.QtWidgets import QApplication
from PySide2.QtWidgets import QOpenGLWidget

from OpenGL import GL as gl

import vapoursynth as vs


class TextureGL(QOpenGLWidget):

    def __init__(self, parent=None):
        QOpenGLWidget.__init__(self, parent)

        self.lut_identity = cms.generate_3dlut(2, None)

        self.new_image = None
        self.new_lut3d = self.lut_identity

        self.context = QOpenGLContext()
        self.program = QOpenGLShaderProgram()

    def cleanUpGl(self):
        del self.program
        self.program = None
        self.doneCurrent()

    def resizeGL(self, width: int, height: int):
        funcs = self.context.functions()
        funcs.glViewport(0, 0, width, height)

    def initializeGL(self):
        self.context.create()
        self.context.aboutToBeDestroyed.connect(self.cleanUpGl)

        funcs = self.context.functions()
        funcs.initializeOpenGLFunctions()
        funcs.glClearColor(0, 0, 0, 1)

        vshader = QOpenGLShader(QOpenGLShader.Vertex)
        vshader.compileSourceFile("texture.vert")
        fshader = QOpenGLShader(QOpenGLShader.Fragment)
        fshader.compileSourceFile("texture.frag")

        self.program = QOpenGLShaderProgram(self.context)
        self.program.addShader(vshader)
        self.program.addShader(fshader)

        self.program.link()
        self.program.bind()

        program_id = self.program.programId()

        yloc = gl.glGetUniformLocation(program_id, "sColor0")
        uloc = gl.glGetUniformLocation(program_id, "sColor1")
        vloc = gl.glGetUniformLocation(program_id, "sColor2")
        lutloc = gl.glGetUniformLocation(program_id, "sLut")

        self.loc = {
          "color_space": gl.glGetUniformLocation(program_id, "in_color_space"),
          "range": gl.glGetUniformLocation(program_id, "in_range"),
          "bit_depth": gl.glGetUniformLocation(program_id, "in_bit_depth"),
        }

        gl.glUniform1i(yloc, 0)
        gl.glUniform1i(uloc, 1)
        gl.glUniform1i(vloc, 2)
        gl.glUniform1i(lutloc, 3)

        gl.glEnable(gl.GL_TEXTURE_2D)
        self.texture = gl.glGenTextures(3)
        self.texture_ids = [gl.GL_TEXTURE0, gl.GL_TEXTURE1, gl.GL_TEXTURE2]

        gl.glEnable(gl.GL_TEXTURE_3D)
        self.lut3d = gl.glGenTextures(1)

    def update_3dlut(self, lut3d):
        self.new_lut3d = lut3d
        self.update()

    def update_image(self, planes, resolutions, color_space, color_range,
                     bit_depth, sample_type):
        self.new_image = (planes, resolutions, color_space, color_range,
                          bit_depth, sample_type)
        self.setFixedSize(resolutions[0][0], resolutions[0][1])
        self.update()

    def paintGL(self):
        funcs = self.context.functions()
        funcs.glClear(gl.GL_COLOR_BUFFER_BIT)

        if self.new_image is not None:
            (planes, resolutions, color_space, color_range, bit_depth,
             sample_type) = self.new_image

            if sample_type == vs.SampleType.FLOAT:
                pixel_stride = gl.GL_FLOAT
                # not done
            elif bit_depth > 8:
                pixel_stride = gl.GL_UNSIGNED_SHORT
            else:
                pixel_stride = gl.GL_UNSIGNED_BYTE

            for i in range(len(planes)):
                gl.glActiveTexture(self.texture_ids[i])
                gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture[i])
                gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
                gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RED,
                                resolutions[i][0], resolutions[i][1], 0,
                                gl.GL_RED, pixel_stride, planes[i].tobytes())
                gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER,
                                   gl.GL_NEAREST)
                gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER,
                                   gl.GL_NEAREST)
                gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S,
                                   gl.GL_CLAMP_TO_EDGE)
                gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T,
                                   gl.GL_CLAMP_TO_EDGE)

            gl.glUniform1i(self.loc["color_space"], color_space)
            gl.glUniform1i(self.loc["range"], color_range)
            gl.glUniform1i(self.loc["bit_depth"], bit_depth)

            self.new_image = None

        if self.new_lut3d is not None:
            (res, lut_data) = self.new_lut3d
            gl.glBindTexture(gl.GL_TEXTURE_3D, self.lut3d)
            gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
            gl.glTexImage3D(gl.GL_TEXTURE_3D, 0, gl.GL_RGB, res, res, res, 0,
                            gl.GL_RGB, gl.GL_UNSIGNED_BYTE, lut_data.tobytes())
            gl.glTexParameteri(gl.GL_TEXTURE_3D, gl.GL_TEXTURE_MAG_FILTER,
                               gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_3D, gl.GL_TEXTURE_MIN_FILTER,
                               gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_3D, gl.GL_TEXTURE_WRAP_S,
                               gl.GL_CLAMP_TO_EDGE)
            gl.glTexParameteri(gl.GL_TEXTURE_3D, gl.GL_TEXTURE_WRAP_T,
                               gl.GL_CLAMP_TO_EDGE)

            self.new_lut3d = None

        self.program.bind()

        for i in range(len(self.texture_ids)):
            gl.glEnable(gl.GL_TEXTURE_2D)
            gl.glActiveTexture(self.texture_ids[i])
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture[i])

        gl.glEnable(gl.GL_TEXTURE_3D)
        gl.glActiveTexture(gl.GL_TEXTURE3)
        gl.glBindTexture(gl.GL_TEXTURE_3D, self.lut3d)

        gl.glBegin(gl.GL_QUADS)
        gl.glTexCoord2d(1, 1)
        gl.glVertex3f(+1, -1, -1)
        gl.glTexCoord2d(0, 1)
        gl.glVertex3f(-1, -1, -1)
        gl.glTexCoord2d(0, 0)
        gl.glVertex3f(-1, 1, -1)
        gl.glTexCoord2d(1, 0)
        gl.glVertex3f(1, 1, -1)

        gl.glEnd()