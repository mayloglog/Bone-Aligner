bl_info = {
    "name": "Bone Aligner",
    "author": "maylog",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "Properties > Data > Bone Aligner",
    "description": "Align all bones with same name between active and selected armatures in Edit Mode",
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

def get_sorted_bones(armature):
    """Return edit bones sorted by hierarchy (parents first)"""
    bones = list(armature.data.edit_bones)
    
    # Sort bones by hierarchy (root to leaf)
    sorted_bones = []
    def add_bone(bone):
        if bone not in sorted_bones:
            if bone.parent:
                add_bone(bone.parent)  # Recursively add parent first
            sorted_bones.append(bone)
    
    for bone in bones:
        add_bone(bone)
    return sorted_bones

class BONEALIGNER_OT_AlignActiveToSelected(Operator):
    """Align all bones in active armature to matching bones in selected armature"""
    bl_idname = "bonealigner.align_active_to_selected"
    bl_label = "Active to Selected"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE' and obj != context.active_object]
        return (context.active_object is not None and
                context.active_object.type == 'ARMATURE' and
                len(selected_armatures) > 0 and
                context.mode == 'EDIT_ARMATURE')

    def execute(self, context):
        return self.align_bones(context, active_to_selected=True)

    def align_bones(self, context, active_to_selected):
        active_armature = context.active_object
        case_sensitive = context.scene.bone_aligner_case_sensitive
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE' and obj != active_armature]
        if not selected_armatures:
            self.report({'ERROR'}, "No other armature selected")
            return {'CANCELLED'}
        selected_armature = selected_armatures[0]

        if context.mode != 'EDIT_ARMATURE':
            self.report({'ERROR'}, "Please switch to Edit Mode")
            return {'CANCELLED'}

        active_bones = get_sorted_bones(active_armature)
        selected_bones = get_sorted_bones(selected_armature)
        aligned_count = 0

        for active_bone in active_bones:
            for selected_bone in selected_bones:
                if self.compare_names(active_bone.name, selected_bone.name, case_sensitive):
                    if active_to_selected:
                        active_bone.head = selected_bone.head
                        active_bone.tail = selected_bone.tail
                        active_bone.matrix = selected_bone.matrix.copy()
                        active_bone.roll = selected_bone.roll
                        self.report({'INFO'}, f"Aligned {active_bone.name} to {selected_bone.name} in Edit Mode")
                    else:
                        selected_bone.head = active_bone.head
                        selected_bone.tail = active_bone.tail
                        selected_bone.matrix = active_bone.matrix.copy()
                        selected_bone.roll = active_bone.roll
                        self.report({'INFO'}, f"Aligned {selected_bone.name} to {active_bone.name} in Edit Mode")
                    aligned_count += 1
                    break

        if aligned_count == 0:
            self.report({'WARNING'}, "No matching bones found between armatures")
        else:
            self.report({'INFO'}, f"Aligned {aligned_count} bone(s)")

        context.view_layer.update()
        return {'FINISHED'}

    def compare_names(self, name1, name2, case_sensitive):
        """Compare bone names based on case sensitivity setting"""
        if case_sensitive:
            return name1 == name2
        return name1.lower() == name2.lower()

class BONEALIGNER_OT_AlignSelectedToActive(Operator):
    """Align all bones in selected armature to matching bones in active armature"""
    bl_idname = "bonealigner.align_selected_to_active"
    bl_label = "Selected to Active"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE' and obj != context.active_object]
        return (context.active_object is not None and
                context.active_object.type == 'ARMATURE' and
                len(selected_armatures) > 0 and
                context.mode == 'EDIT_ARMATURE')

    def execute(self, context):
        return self.align_bones(context, active_to_selected=False)

    def align_bones(self, context, active_to_selected):
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
        return (context.active_object and
                context.active_object.type == 'ARMATURE' and
                context.mode == 'EDIT_ARMATURE')

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # UI controls (only shown in Edit Mode)
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