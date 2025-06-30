bl_info = {
    "name": "Bone Aligner",
    "author": "maylog",
    "version": (1, 0, 2),
    "blender": (4, 0, 0),
    "location": "Properties > Data > Bone Aligner",
    "description": "Align all bones with same name between active and selected armatures in Edit Mode",
    "category": "Rigging",
}

import bpy
import mathutils
from bpy.types import Operator, Panel, Object
from bpy.props import BoolProperty

# Define scene property for case sensitivity
def register_scene_properties():
    """Register scene property for case sensitivity."""
    bpy.types.Scene.bone_aligner_case_sensitive = BoolProperty(
        name="Case Sensitive",
        description="Match bone names with case sensitivity",
        default=True
    )

def compare_names(name1: str, name2: str, case_sensitive: bool) -> bool:
    """Compare bone names based on case sensitivity setting."""
    if case_sensitive:
        return name1 == name2
    return name1.lower() == name2.lower()

def get_sorted_bones(armature: Object) -> list:
    """Return edit bones sorted by hierarchy (parents first) using non-recursive DFS.
    
    Args:
        armature: The armature object containing edit bones.
    
    Returns:
        List of edit bones sorted from root to leaf.
    """
    bones = list(armature.data.edit_bones)
    sorted_bones = []
    visited = set()

    def topological_sort(bone):
        if bone.name not in visited:
            visited.add(bone.name)
            if bone.parent:
                topological_sort(bone.parent)
            sorted_bones.append(bone)

    for bone in bones:
        topological_sort(bone)
    
    return sorted_bones

class BONEALIGNER_OT_AlignActiveToSelected(Operator):
    """Align all bones in active armature to matching bones in selected armature."""
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

    def align_bones(self, context, active_to_selected: bool):
        """Align bones between active and selected armatures.

        Args:
            context: Blender context.
            active_to_selected: If True, align active to selected; else, selected to active.
        
        Returns:
            {'FINISHED'} on success, {'CANCELLED'} on error.
        """
        active_armature = context.active_object
        case_sensitive = context.scene.bone_aligner_case_sensitive
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE' and obj != active_armature]
        
        if not selected_armatures:
            self.report({'ERROR'}, "No other armature selected")
            return {'CANCELLED'}
        selected_armature = selected_armatures[0]

        # Validate armatures
        if not active_armature.data.edit_bones or not selected_armature.data.edit_bones:
            self.report({'ERROR'}, "One or both armatures have no bones")
            return {'CANCELLED'}

        # Create dictionary for selected bones to optimize lookup
        selected_bones = get_sorted_bones(selected_armature)
        selected_bone_dict = {bone.name: bone for bone in selected_bones}
        active_bones = get_sorted_bones(active_armature)
        aligned_count = 0

        for active_bone in active_bones:
            compare_name = active_bone.name if case_sensitive else active_bone.name.lower()
            target_bone = selected_bone_dict.get(compare_name if case_sensitive else compare_name.lower())
            if target_bone:
                if active_to_selected:
                    active_bone.head = target_bone.head
                    active_bone.tail = target_bone.tail
                    active_bone.matrix = target_bone.matrix.copy()
                    active_bone.roll = target_bone.roll
                    self.report({'INFO'}, f"Aligned {active_bone.name} to {target_bone.name} in Edit Mode")
                else:
                    target_bone.head = active_bone.head
                    target_bone.tail = active_bone.tail
                    target_bone.matrix = active_bone.matrix.copy()
                    target_bone.roll = active_bone.roll
                    self.report({'INFO'}, f"Aligned {target_bone.name} to {active_bone.name} in Edit Mode")
                aligned_count += 1

        if aligned_count == 0:
            self.report({'WARNING'}, "No matching bones found between armatures")
        else:
            self.report({'INFO'}, f"Aligned {aligned_count} bone(s)")

        context.view_layer.update()
        return {'FINISHED'}

class BONEALIGNER_OT_AlignSelectedToActive(Operator):
    """Align all bones in selected armature to matching bones in active armature."""
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
        return BONEALIGNER_OT_AlignActiveToSelected.align_bones(self, context, active_to_selected=False)

class BONEALIGNER_PT_Panel(Panel):
    """Panel for Bone Aligner in Armature Data Properties."""
    bl_label = "Bone Aligner"
    bl_idname = "BONEALIGNER_PT_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    bl_category = "Bone Aligner"

    @classmethod
    def poll(cls, context):
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE' and obj != context.active_object]
        return (context.active_object and
                context.active_object.type == 'ARMATURE' and
                len(selected_armatures) > 0 and
                context.mode == 'EDIT_ARMATURE')

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # UI controls
        layout.prop(scene, "bone_aligner_case_sensitive", text="Case Sensitive")
        layout.operator(BONEALIGNER_OT_AlignActiveToSelected.bl_idname, text="Active to Selected")
        layout.operator(BONEALIGNER_OT_AlignSelectedToActive.bl_idname, text="Selected to Active")
        layout.label(text="Select two armatures to align their bones.")

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