bl_info = {
    "name": "Bone Aligner",
    "author": "maylog",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "Properties > Data > Bone Aligner",
    "description": "Align bones between active and selected with same name based on current mode",
    "category": "Animation",
}

import bpy
import mathutils
from bpy.types import Operator, Panel
from bpy.props import BoolProperty

# Define scene property for case sensitivity
def register_scene_properties():
    bpy.types.Scene.bone_aligner_case_sensitive = BoolProperty(
        name="Case Sensitive",
        description="Match bone names with case sensitivity",
        default=True
    )

class BONEALIGNER_OT_AlignActiveToSelected(Operator):
    """Align active bone to selected bone with same name"""
    bl_idname = "bonealigner.align_active_to_selected"
    bl_label = "Active to Selected"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and
                context.active_object.type == 'ARMATURE')

    def execute(self, context):
        return self.align_bones(context, active_to_selected=True)

    def align_bones(self, context, active_to_selected):
        armature = context.active_object
        case_sensitive = context.scene.bone_aligner_case_sensitive
        aligned = False

        if context.mode == 'EDIT_ARMATURE':
            edit_bones = armature.data.edit_bones
            active_bone = edit_bones.active

            if active_bone:
                for selected_bone in context.selected_editable_bones:  # Fixed typo
                    if selected_bone != active_bone:
                        if self.compare_names(active_bone.name, selected_bone.name, case_sensitive):
                            if active_to_selected:
                                # Align active to selected
                                active_bone.head = selected_bone.head
                                active_bone.tail = selected_bone.tail
                                active_bone.matrix = selected_bone.matrix.copy()
                                active_bone.roll = selected_bone.roll
                                self.report({'INFO'}, f"Aligned {active_bone.name} to {selected_bone.name} in Edit Mode")
                            else:
                                # Align selected to active
                                selected_bone.head = active_bone.head
                                selected_bone.tail = active_bone.tail
                                selected_bone.matrix = active_bone.matrix.copy()
                                selected_bone.roll = active_bone.roll
                                self.report({'INFO'}, f"Aligned {selected_bone.name} to {active_bone.name} in Edit Mode")
                            aligned = True
                            break
                if not aligned:
                    self.report({'WARNING'}, f"No matching bone found for {active_bone.name}")
            else:
                self.report({'WARNING'}, "No active bone selected")
                return {'CANCELLED'}

        elif context.mode == 'POSE':
            pose_bones = armature.pose.bones
            active_bone = context.active_pose_bone

            if active_bone:
                for selected_bone in context.selected_pose_bones:
                    if selected_bone != active_bone:
                        if self.compare_names(active_bone.name, selected_bone.name, case_sensitive):
                            if active_to_selected:
                                # Align active to selected
                                active_bone.matrix = selected_bone.matrix.copy()
                                self.report({'INFO'}, f"Aligned {active_bone.name} to {selected_bone.name} in Pose Mode")
                            else:
                                # Align selected to active
                                selected_bone.matrix = active_bone.matrix.copy()
                                self.report({'INFO'}, f"Aligned {selected_bone.name} to {active_bone.name} in Pose Mode")
                            aligned = True
                            break
                if not aligned:
                    self.report({'WARNING'}, f"No matching bone found for {active_bone.name}")
            else:
                self.report({'WARNING'}, "No active pose bone selected")
                return {'CANCELLED'}

        else:
            self.report({'ERROR'}, "Please switch to Edit Mode or Pose Mode")
            return {'CANCELLED'}

        context.view_layer.update()
        return {'FINISHED'}

    def compare_names(self, name1, name2, case_sensitive):
        """Compare bone names based on case sensitivity setting"""
        if case_sensitive:
            return name1 == name2
        return name1.lower() == name2.lower()

class BONEALIGNER_OT_AlignSelectedToActive(Operator):
    """Align selected bone with same name to active bone"""
    bl_idname = "bonealigner.align_selected_to_active"
    bl_label = "Selected to Active"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and
                context.active_object.type == 'ARMATURE')

    def execute(self, context):
        return self.align_bones(context, active_to_selected=False)

    def align_bones(self, context, active_to_selected):
        # Reuse the align_bones method from BONEALIGNER_OT_AlignActiveToSelected
        return BONEALIGNER_OT_AlignActiveToSelected.align_bones(self, context, active_to_selected)

    def compare_names(self, name1, name2, case_sensitive):
        return BONEALIGNER_OT_AlignActiveToSelected.compare_names(self, name1, name2, case_sensitive)

class BONEALIGNER_PT_Panel(Panel):
    """Panel for Bone Aligner in Armature Data Properties"""
    bl_label = "Bone Aligner"
    bl_idname = "BONEALIGNER_PT_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    bl_category = "Bone Aligner"

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # UI controls
        layout.prop(scene, "bone_aligner_case_sensitive", text="Case Sensitive")
        layout.operator(BONEALIGNER_OT_AlignActiveToSelected.bl_idname, text="Active to Selected")
        layout.operator(BONEALIGNER_OT_AlignSelectedToActive.bl_idname, text="Selected to Active")

def register():
    register_scene_properties()
    bpy.utils.register_class(BONEALIGNER_OT_AlignActiveToSelected)
    bpy.utils.register_class(BONEALIGNER_OT_AlignSelectedToActive)
    bpy.utils.register_class(BONEALIGNER_PT_Panel)

def unregister():
    bpy.utils.unregister_class(BONEALIGNER_OT_AlignActiveToSelected)
    bpy.utils.unregister_class(BONEALIGNER_OT_AlignSelectedToActive)
    bpy.utils.unregister_class(BONEALIGNER_PT_Panel)
    del bpy.types.Scene.bone_aligner_case_sensitive

if __name__ == "__main__":
    register()