bl_info = {
    "name": "Bone Aligner",
    "author": "maylog",
    "version": (1, 1, 1),
    "blender": (4, 0, 0),
    "location": "Properties > Data > Bone Aligner",
    "description": "Align or rename bones in Edit Mode, or add/clear Copy Transforms constraints in Pose Mode",
    "category": "Animation",
}

import bpy
import mathutils
from bpy.types import Operator, Panel, Object
from bpy.props import BoolProperty

# Define scene properties
def register_scene_properties():
    """Register scene property for case sensitivity."""
    bpy.types.Scene.bone_aligner_case_sensitive = BoolProperty(
        name="Case Sensitive", description="Match bone names with case sensitivity", default=True
    )

def compare_names(name1: str, name2: str, case_sensitive: bool) -> bool:
    """Compare bone names based on case sensitivity setting."""
    return name1 == name2 if case_sensitive else name1.lower() == name2.lower()

def get_sorted_bones(armature: Object) -> list:
    """Return edit bones sorted by hierarchy (parents first) using non-recursive DFS."""
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
    """Align all bones in active armature to matching bones in selected armature in Edit Mode."""
    bl_idname = "bonealigner.align_active_to_selected"
    bl_label = "Active to Selected"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
        return (context.active_object and
                context.active_object.type == 'ARMATURE' and
                len(selected_armatures) >= 2 and
                context.mode == 'EDIT_ARMATURE')

    def execute(self, context):
        return self.align_bones(context, active_to_selected=True)

    def align_bones(self, context, active_to_selected: bool):
        """Align bones between active and selected armatures in Edit Mode."""
        active_armature = context.active_object
        case_sensitive = context.scene.bone_aligner_case_sensitive
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE' and obj != active_armature]
        
        if not selected_armatures:
            self.report({'ERROR'}, "No other armature selected")
            return {'CANCELLED'}
        selected_armature = selected_armatures[0]

        if not active_armature.data.edit_bones or not selected_armature.data.edit_bones:
            self.report({'ERROR'}, "One or both armatures have no bones")
            return {'CANCELLED'}

        selected_bones = get_sorted_bones(selected_armature)
        selected_bone_dict = {bone.name: bone for bone in selected_bones}
        active_bones = get_sorted_bones(active_armature)
        aligned_count = 0
        unmatched_bones = []

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
                    target_bone.roll = target_bone.roll
                    self.report({'INFO'}, f"Aligned {target_bone.name} to {active_bone.name} in Edit Mode")
                aligned_count += 1
            else:
                unmatched_bones.append(active_bone.name)

        if aligned_count == 0:
            self.report({'WARNING'}, f"No matching bones found. Active armature bones: {', '.join(unmatched_bones)}")
        else:
            self.report({'INFO'}, f"Aligned {aligned_count} bone(s)")

        context.view_layer.update()
        return {'FINISHED'}

class BONEALIGNER_OT_AlignSelectedToActive(Operator):
    """Align all bones in selected armature to matching bones in active armature in Edit Mode."""
    bl_idname = "bonealigner.align_selected_to_active"
    bl_label = "Selected to Active"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
        return (context.active_object and
                context.active_object.type == 'ARMATURE' and
                len(selected_armatures) >= 2 and
                context.mode == 'EDIT_ARMATURE')

    def execute(self, context):
        return BONEALIGNER_OT_AlignActiveToSelected.align_bones(self, context, active_to_selected=False)

class BONEALIGNER_OT_RenameSelectedToActive(Operator):
    """Rename selected bone to match active bone's name in Edit Mode."""
    bl_idname = "bonealigner.rename_selected_to_active"
    bl_label = "Selected to Active Name"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object and
                context.active_object.type == 'ARMATURE' and
                context.mode == 'EDIT_ARMATURE' and
                len(context.selected_editable_bones) == 2)

    def execute(self, context):
        """Rename selected bone to active bone's name, handling conflicts."""
        bones = context.selected_editable_bones
        active_bone = context.active_bone
        selected_bone = next(b for b in bones if b != active_bone)

        if not active_bone or not selected_bone:
            self.report({'ERROR'}, "Active or selected bone not found")
            return {'CANCELLED'}

        if active_bone.name == selected_bone.name:
            self.report({'WARNING'}, f"Selected bone already named '{active_bone.name}'")
            return {'CANCELLED'}

        try:
            old_name = selected_bone.name
            selected_bone.name = active_bone.name
            self.report({'INFO'}, f"Renamed bone '{old_name}' to '{selected_bone.name}'")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to rename bone: {str(e)}")
            return {'CANCELLED'}

        context.view_layer.update()
        return {'FINISHED'}

class BONEALIGNER_OT_RenameActiveToSelected(Operator):
    """Rename active bone to match selected bone's name in Edit Mode."""
    bl_idname = "bonealigner.rename_active_to_selected"
    bl_label = "Active to Selected Name"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object and
                context.active_object.type == 'ARMATURE' and
                context.mode == 'EDIT_ARMATURE' and
                len(context.selected_editable_bones) == 2)

    def execute(self, context):
        """Rename active bone to selected bone's name, handling conflicts."""
        bones = context.selected_editable_bones
        active_bone = context.active_bone
        selected_bone = next(b for b in bones if b != active_bone)

        if not active_bone or not selected_bone:
            self.report({'ERROR'}, "Active or selected bone not found")
            return {'CANCELLED'}

        if active_bone.name == selected_bone.name:
            self.report({'WARNING'}, f"Active bone already named '{selected_bone.name}'")
            return {'CANCELLED'}

        try:
            old_name = active_bone.name
            active_bone.name = selected_bone.name
            self.report({'INFO'}, f"Renamed bone '{old_name}' to '{active_bone.name}'")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to rename bone: {str(e)}")
            return {'CANCELLED'}

        context.view_layer.update()
        return {'FINISHED'}

class BONEALIGNER_OT_AlignActiveToSelectedPose(Operator):
    """Add Copy Transforms constraints to active armature's bones targeting selected armature in Pose Mode."""
    bl_idname = "bonealigner.align_active_to_selected_pose"
    bl_label = "Active to Selected"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
        return (context.active_object and
                context.active_object.type == 'ARMATURE' and
                len(selected_armatures) >= 1 and
                context.mode == 'POSE')

    def execute(self, context):
        return self.add_constraints(context, active_to_selected=True)

    def add_constraints(self, context, active_to_selected: bool):
        """Add Copy Transforms constraints to matching bones in Pose Mode."""
        active_armature = context.active_object
        case_sensitive = context.scene.bone_aligner_case_sensitive
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE' and obj != active_armature]
        
        if not selected_armatures:
            self.report({'ERROR'}, "No other armature selected")
            return {'CANCELLED'}
        selected_armature = selected_armatures[0]

        if not active_armature.data.bones or not selected_armature.data.bones:
            self.report({'ERROR'}, "One or both armatures have no bones")
            return {'CANCELLED'}

        selected_bone_dict = {bone.name: bone for bone in selected_armature.pose.bones}
        active_bones = [bone for bone in active_armature.pose.bones]
        aligned_count = 0
        unmatched_bones = []

        for active_bone in active_bones:
            compare_name = active_bone.name if case_sensitive else active_bone.name.lower()
            target_bone = selected_bone_dict.get(compare_name if case_sensitive else compare_name.lower())
            if target_bone:
                source_armature = selected_armature if active_to_selected else active_armature
                dest_armature = active_armature if active_to_selected else selected_armature
                source_bone = target_bone if active_to_selected else active_bone
                dest_bone = active_bone if active_to_selected else target_bone

                for constraint in dest_bone.constraints:
                    if (constraint.type == 'COPY_TRANSFORMS' and
                        constraint.target == source_armature and
                        constraint.subtarget == source_bone.name):
                        dest_bone.constraints.remove(constraint)

                constraint = dest_bone.constraints.new('COPY_TRANSFORMS')
                constraint.target = source_armature
                constraint.subtarget = source_bone.name
                constraint.target_space = 'WORLD'
                constraint.owner_space = 'WORLD'
                constraint.mute = False

                self.report({'INFO'}, f"Added constraint to {dest_bone.name} targeting {source_bone.name}")
                aligned_count += 1
            else:
                unmatched_bones.append(active_bone.name)

        if aligned_count == 0:
            self.report({'WARNING'}, f"No matching bones found. Active armature bones: {', '.join(unmatched_bones)}")
        else:
            self.report({'INFO'}, f"Added constraints to {aligned_count} bone(s)")

        context.view_layer.update()
        return {'FINISHED'}

class BONEALIGNER_OT_AlignSelectedToActivePose(Operator):
    """Add Copy Transforms constraints to selected armature's bones targeting active armature in Pose Mode."""
    bl_idname = "bonealigner.align_selected_to_active_pose"
    bl_label = "Selected to Active"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
        return (context.active_object and
                context.active_object.type == 'ARMATURE' and
                len(selected_armatures) >= 1 and
                context.mode == 'POSE')

    def execute(self, context):
        return BONEALIGNER_OT_AlignActiveToSelectedPose.add_constraints(self, context, active_to_selected=False)

class BONEALIGNER_OT_ClearConstraints(Operator):
    """Clear all constraints from selected pose bones in Pose Mode."""
    bl_idname = "bonealigner.clear_constraints"
    bl_label = "Clear Constraints"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object and
                context.active_object.type == 'ARMATURE' and
                context.mode == 'POSE')

    def execute(self, context):
        """Clear all constraints from selected pose bones."""
        selected_bones = context.selected_pose_bones or []
        if not selected_bones:
            self.report({'ERROR'}, "No pose bones selected")
            return {'CANCELLED'}

        cleared_count = 0
        for bone in selected_bones:
            for constraint in bone.constraints:
                bone.constraints.remove(constraint)
                cleared_count += 1

        if cleared_count == 0:
            self.report({'INFO'}, "No constraints found to clear")
        else:
            self.report({'INFO'}, f"Cleared {cleared_count} constraint(s) from selected bones")

        context.view_layer.update()
        return {'FINISHED'}

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
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
        if context.mode == 'EDIT_ARMATURE':
            return (context.active_object and
                    context.active_object.type == 'ARMATURE' and
                    len(selected_armatures) >= 2)
        elif context.mode == 'POSE':
            return (context.active_object and
                    context.active_object.type == 'ARMATURE' and
                    len(selected_armatures) >= 1)
        return False

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Vertical layout for case sensitive and buttons
        layout.prop(scene, "bone_aligner_case_sensitive", text="Case Sensitive")
        if context.mode == 'EDIT_ARMATURE':
            layout.operator(BONEALIGNER_OT_AlignActiveToSelected.bl_idname, text="Active to Selected")
            layout.operator(BONEALIGNER_OT_AlignSelectedToActive.bl_idname, text="Selected to Active")
            if len(context.selected_editable_bones) == 2:
                layout.operator(BONEALIGNER_OT_RenameSelectedToActive.bl_idname, text="Selected to Active Name")
                layout.operator(BONEALIGNER_OT_RenameActiveToSelected.bl_idname, text="Active to Selected Name")
            layout.label(text="Align or rename bones in Edit Mode.")
        elif context.mode == 'POSE':
            layout.operator(BONEALIGNER_OT_AlignActiveToSelectedPose.bl_idname, text="Active to Selected")
            layout.operator(BONEALIGNER_OT_AlignSelectedToActivePose.bl_idname, text="Selected to Active")
            layout.operator(BONEALIGNER_OT_ClearConstraints.bl_idname, text="Clear Constraints")
            layout.label(text="Add or clear constraints in Pose Mode. Select bones and press Alt to change constraint space.")

def register():
    register_scene_properties()
    bpy.utils.register_class(BONEALIGNER_OT_AlignActiveToSelected)
    bpy.utils.register_class(BONEALIGNER_OT_AlignSelectedToActive)
    bpy.utils.register_class(BONEALIGNER_OT_RenameSelectedToActive)
    bpy.utils.register_class(BONEALIGNER_OT_RenameActiveToSelected)
    bpy.utils.register_class(BONEALIGNER_OT_AlignActiveToSelectedPose)
    bpy.utils.register_class(BONEALIGNER_OT_AlignSelectedToActivePose)
    bpy.utils.register_class(BONEALIGNER_OT_ClearConstraints)
    bpy.utils.register_class(BONEALIGNER_PT_Panel)

def unregister():
    bpy.utils.unregister_class(BONEALIGNER_OT_AlignActiveToSelected)
    bpy.utils.unregister_class(BONEALIGNER_OT_AlignSelectedToActive)
    bpy.utils.unregister_class(BONEALIGNER_OT_RenameSelectedToActive)
    bpy.utils.unregister_class(BONEALIGNER_OT_RenameActiveToSelected)
    bpy.utils.unregister_class(BONEALIGNER_OT_AlignActiveToSelectedPose)
    bpy.utils.unregister_class(BONEALIGNER_OT_AlignSelectedToActivePose)
    bpy.utils.unregister_class(BONEALIGNER_OT_ClearConstraints)
    bpy.utils.unregister_class(BONEALIGNER_PT_Panel)
    del bpy.types.Scene.bone_aligner_case_sensitive

if __name__ == "__main__":
    register()