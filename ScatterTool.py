import random
import logging
import maya.cmds as cmds
import maya.OpenMayaUI as omui
from PySide import QtCore, QtGui
from shiboken import wrapInstance

import scatter_form

def maya_main_window():
    """
    Utility method to get the main maya parent window
    """
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(main_window_ptr), QtGui.QWidget)


class ScatterTool(QtGui.QMainWindow):
 
    def __init__(self, parent=maya_main_window()):
        super(ScatterTool, self).__init__(parent)

        self.ui = scatter_form.Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.load_surface_btn.clicked.connect(self.load_surface)
        self.ui.load_object_btn.clicked.connect(self.load_object)
        self.ui.do_scatter_btn.clicked.connect(self.do_scatter)

        self.surface = None
        self.object = None

    def load_surface(self):

        """
        Method to load in memory the pointer to the surface mesh
        """

        selection = cmds.ls(selection=True)

        if len(selection) != 1:
            message = "You nead to select one and only one object!"
            response = QtGui.QMessageBox.question(self, "Selection", message)

        else:

            surface = selection[0]

            if surface != self.object:

                self.surface = surface

                self.ui.surface_name_dpy.setText(surface)

            else:
                message = "Surface and object can't be the same!"
                response = QtGui.QMessageBox.question(self, "Conflict!", message)


    def load_object(self):

        """
        Method to load in memory the pointer to the mesh to be scattered
        """

        selection = cmds.ls(selection=True)

        if len(selection) != 1:
            message = "You nead to select one and only one object!"
            response = QtGui.QMessageBox.question(self, "Selection", message)

        else:

            object = selection[0]

            if object != self.surface:

                self.object = object

                self.ui.object_name_dpy.setText(object)

            else:
                message = "Surface and object can't be the same!"
                response = QtGui.QMessageBox.question(self, "Conflict!", message)

    def randomize_wire_color(self, node):

        """
        Method to randomize color override index by user defined range
        """

        random_index = random.randint(self.ui.min_hue_spn.value(), self.ui.max_hue_spn.value())

        cmds.setAttr("%s.overrideEnabled" % node, True)
        cmds.setAttr("%s.overrideColor" % node, random_index)


    def do_scatter(self):

        """
        Main runtime point for the scatter mecanism
        """

        if self.surface and self.object:

            self.copied_nodes = []

            self.copies = self.ui.num_copies_spn.value()
            self.scale_min = self.ui.min_scale_spn.value()
            self.scale_max = self.ui.max_scale_spn.value()

            if self.ui.scatter_method_cmb.currentText() == 'Faces':
                self.scatter_by_faces()
            else:
                self.scatter_by_volume()

            self.group_nodes()

        else:
            message = "You nead to load surface and object nodes!"
            response = QtGui.QMessageBox.question(self, "Missing Nodes", message)

    def copy_obj(self):

        """
        Method to define the copy type, Duplicate or Instancing
        """

        if self.ui.copy_type_cmb.currentText() == 'Duplicate':
            new_obj = cmds.duplicate(self.object)[0]
        else:
            new_obj = cmds.instance(self.object)[0]

        return new_obj

    def group_nodes(self):

        """
        Method that ensure the resulted scattered nodes will be grouped
        """

        if len(self.copied_nodes) > 1:

            group_name = "CopiesGroup"

            goup_node = cmds.objExists(group_name)

            if goup_node:

                flags = QtGui.QMessageBox.StandardButton.Yes 
                flags |= QtGui.QMessageBox.StandardButton.No
                question = 'A group node named "%s" already exists, do you what to use it?\n' % group_name
                question += 'If no, then a new one with a number sufix will be created'
                response = QtGui.QMessageBox.question(self, "Group Node",
                                                      question,
                                                      flags)
                if response == QtGui.QMessageBox.Yes:
                    goup_node = group_name

                else:
                    goup_node = cmds.createNode("transform", name=group_name)

            else:
                goup_node = cmds.createNode("transform", name=group_name)

            for node in self.copied_nodes:
                cmds.parent(node, goup_node)

    def scatter_by_faces(self):

        """
        Method to scatter node by target surface faces
        """

        face_count = cmds.polyEvaluate(self.surface, f=True )

        if face_count >= self.copies:

            face_num_list = range(1, face_count + 1)
            random.shuffle(face_num_list)

            for face_num in face_num_list[0:self.copies]:
                
                current_face = "%s.f[%s]" % (self.surface, face_num)
                
                face_wsp = cmds.xform(current_face, query=True, worldSpace=True, boundingBox=True)
                xmin, ymin, zmin, xmax, ymax, zmax = face_wsp
                
                pos_x = xmin + ((xmax - xmin) / 2)
                pos_y = ymin + ((ymax - ymin) / 2)
                pos_z = zmin + ((zmax - zmin) / 2)
                
                new_obj = self.copy_obj()

                cmds.setAttr("%s.tx" % new_obj, float(pos_x))
                cmds.setAttr("%s.ty" % new_obj, float(pos_y))
                cmds.setAttr("%s.tz" % new_obj, float(pos_z))
                
                random_scale = random.uniform(self.scale_min, self.scale_max)
                cmds.setAttr("%s.scaleX" % new_obj, random_scale)
                cmds.setAttr("%s.scaleY" % new_obj, random_scale)
                cmds.setAttr("%s.scaleZ" % new_obj, random_scale)
                
                constraint = cmds.normalConstraint(current_face,
                                                   new_obj,
                                                   aimVector=[0, 1, 0],
                                                   upVector=[0,1,0],
                                                   worldUpType="scene")
                cmds.delete(constraint)

                self.randomize_wire_color(new_obj)

                self.copied_nodes.append(new_obj)
        else:
            message = "With Faces method You need to specify a number of copies"
            message += "\nsmaller or equal the faces on the surface node!\n"
            message += "Currently the surface has %s faces" % face_count
            response = QtGui.QMessageBox.question(self, "Face count - Copies", message)


    def scatter_by_volume(self):

        """
        Method to scatter node by target surface volume/area
        """

        surface_wsp = cmds.xform(self.surface, query=True, worldSpace=True, boundingBox=True)
        xmin, ymin, zmin, xmax, ymax, zmax = surface_wsp

        for copy_num in range(1, self.copies + 1):

            pos_x = random.uniform(xmin, xmax)
            pos_y = random.uniform(ymin, ymax)
            pos_z = random.uniform(zmin, zmax)

            new_obj = self.copy_obj()

            cmds.setAttr("%s.tx" % new_obj, float(pos_x))
            cmds.setAttr("%s.ty" % new_obj, float(pos_y))
            cmds.setAttr("%s.tz" % new_obj, float(pos_z))

            random_scale = random.uniform(self.scale_min, self.scale_max)
            cmds.setAttr("%s.scaleX" % new_obj, random_scale)
            cmds.setAttr("%s.scaleY" % new_obj, random_scale)
            cmds.setAttr("%s.scaleZ" % new_obj, random_scale)

            g_constrain = cmds.geometryConstraint(self.surface, new_obj, weight=10)

            n_constraint = cmds.normalConstraint(self.surface,
                                               new_obj,
                                               aimVector=[0, 1, 0],
                                               upVector=[0,1,0],
                                               worldUpType="scene")
            cmds.delete(n_constraint)
            cmds.delete(g_constrain)

            self.randomize_wire_color(new_obj)

            self.copied_nodes.append(new_obj)

def run():
    try:
        ScatterTool.close()
    except:
        pass
    
    tool = ScatterTool()
    tool.show()