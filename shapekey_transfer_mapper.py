bl_info = {
    "name": "Shapekey Transfer & Mapper",
    "author": "Your Name",
    "version": (1, 0, 0),
    "blender": (4, 5, 5),
    "location": "View3D > N Panel > Face Tools",
    "description": "Transfer and map shapekeys between SOURCE (MMD) and TARGET meshes with flexible mapping rules",
    "category": "Animation",
}

import bpy
import json
import re
from typing import Dict, List, Tuple, Optional, Any
from bpy.props import (
    StringProperty, BoolProperty, EnumProperty,
    IntProperty, FloatProperty, PointerProperty,
    CollectionProperty
)
from bpy.types import Operator, Panel, PropertyGroup


# ============================================================================
# PROPERTY GROUPS
# ============================================================================

class ShapekeyMappingRule(PropertyGroup):
    """Single mapping rule"""
    source_name: StringProperty(name="Source", default="")
    target_name: StringProperty(name="Target", default="")
    weight: FloatProperty(name="Weight", default=1.0, min=0.0, max=10.0)
    use_regex: BoolProperty(name="Use Regex", default=False)


class ShapekeyTransferSettings(PropertyGroup):
    """Main add-on settings stored in scene"""
    source_object: PointerProperty(
        name="Source Object",
        type=bpy.types.Object,
        description="Source mesh with MMD shapekeys"
    )
    target_object: PointerProperty(
        name="Target Object",
        type=bpy.types.Object,
        description="Target mesh with your shapekey system"
    )
    
    # Mode selection
    transfer_mode: EnumProperty(
        name="Transfer Mode",
        items=[
            ('DRIVER', "Driver Mode", "Create drivers between shapekeys"),
            ('BAKE', "Bake Mode", "Bake keyframes to new action"),
            ('LIVE', "Live Copy Mode", "Copy values on frame update"),
        ],
        default='DRIVER'
    )
    
    # Driver mode settings
    driver_direction: EnumProperty(
        name="Driver Direction",
        items=[
            ('SOURCE_TO_TARGET', "SOURCE → TARGET", "Source drives target"),
            ('TARGET_TO_SOURCE', "TARGET → SOURCE", "Target drives source"),
        ],
        default='SOURCE_TO_TARGET'
    )
    
    # Bake mode settings
    bake_start_frame: IntProperty(name="Start Frame", default=1)
    bake_end_frame: IntProperty(name="End Frame", default=250)
    bake_step: IntProperty(name="Step", default=1, min=1)
    use_scene_range: BoolProperty(name="Use Scene Range", default=True)
    
    # Live copy settings
    live_copy_enabled: BoolProperty(name="Live Copy Enabled", default=False)
    live_copy_direction: EnumProperty(
        name="Copy Direction",
        items=[
            ('SOURCE_TO_TARGET', "SOURCE → TARGET", ""),
            ('TARGET_TO_SOURCE', "TARGET → SOURCE", ""),
        ],
        default='SOURCE_TO_TARGET'
    )
    
    # Mapping storage
    mapping_json: StringProperty(
        name="Mapping JSON",
        default="",
        description="JSON mapping data"
    )
    
    # UI state
    show_unmapped_source: BoolProperty(name="Show Unmapped Source", default=True)
    show_unmapped_target: BoolProperty(name="Show Unmapped Target", default=True)
    
    # Global driver settings
    driver_clamp_min: FloatProperty(name="Clamp Min", default=0.0)
    driver_clamp_max: FloatProperty(name="Clamp Max", default=1.0)
    driver_scale: FloatProperty(name="Scale", default=1.0, min=0.0, max=10.0)


# ============================================================================
# JSON MAPPING SYSTEM
# ============================================================================

"""
JSON Mapping Format Specification:

{
    "preset_name": "MMD_to_Fac_v1",
    "direction_default": "SOURCE_TO_TARGET",
    "rules": [
        {
            "source": "あ",
            "targets": [
                {"name": "Fac_Mth_Aa1", "weight": 1.0}
            ]
        },
        {
            "source": "ウィンク右",
            "targets": [
                {"name": "Fac_Eye_R_Wink", "weight": 1.0},
                {"name": "Fac_Eye_R_HalfClose", "weight": 0.3}
            ]
        },
        {
            "source_regex": "ウィンク.*右|wink.*r",
            "targets": [
                {"name": "Fac_Eye_R_Wink", "weight": 1.0}
            ]
        }
    ],
    "aliases": {
        "怒り": ["angry", "anger"],
        "困る": ["trouble", "sad", "worried"]
    },
    "global_settings": {
        "clamp_min": 0.0,
        "clamp_max": 1.0,
        "scale": 1.0
    }
}
"""

def create_default_mapping() -> Dict[str, Any]:
    """Create default mapping preset for MMD to Face system"""
    return {
        "preset_name": "MMD_to_Fac_v1",
        "direction_default": "SOURCE_TO_TARGET",
        "rules": [
            {
                "source": "あ",
                "targets": [{"name": "Fac_Mth_AaTalk", "weight": 1.0}]
            },
            {
                "source": "い",
                "targets": [{"name": "Fac_Mth_Ii", "weight": 1.0}]
            },
            {
                "source": "う",
                "targets": [{"name": "Fac_Mth_Uu0", "weight": 1.0}]
            },
            {
                "source": "え",
                "targets": [{"name": "Fac_Mth_Ee", "weight": 1.0}]
            },
            {
                "source": "お",
                "targets": [{"name": "Fac_Mth_Oo", "weight": 1.0}]
            },
            {
                "source": "ウィンク",
                "targets": [
                    {"name": "Fac_Eye_L_Wink", "weight": 1.0}
                ]
            },
            {
                "source": "ウィンク右",
                "targets": [
                    {"name": "Fac_Eye_R_Wink", "weight": 1.0}
                ]
            },
            {
                "source_regex": "ウィンク.*左|wink.*l",
                "targets": [
                    {"name": "Fac_Eye_L_Wink", "weight": 1.0}
                ]
            },
            {
                "source": "にこり",
                "targets": [{"name": "Fac_Smile", "weight": 1.0}]
            },
            {
                "source": "怒り",
                "targets": [{"name": "Fac_Angry", "weight": 1.0}]
            },
            {
                "source": "困る",
                "targets": [{"name": "Fac_Worried", "weight": 1.0}]
            },
        ],
        "aliases": {
            "あ": ["aa", "ah", "AaTalk"],
            "い": ["ii", "ee", "Ii"],
            "う": ["uu", "Uu0"],
            "え": ["ee", "Ee"],
            "お": ["oo", "Oo"],
            "ウィンク": ["wink", "Wink", "eye_close"],
            "ウィンク右": ["wink_r", "Wink_R", "eye_close_r"],
            "ウィンク左": ["wink_l", "Wink_L", "eye_close_l"],
            "にこり": ["smile", "happy", "grin"],
            "怒り": ["angry", "anger", "mad"],
            "困る": ["trouble", "sad", "worried", "concerned"]
        },
        "global_settings": {
            "clamp_min": 0.0,
            "clamp_max": 1.0,
            "scale": 1.0
        }
    }


def load_mapping_json(json_str: str) -> Dict[str, Any]:
    """Load and validate mapping JSON"""
    try:
        data = json.loads(json_str)
        # Validate structure
        if not isinstance(data, dict):
            raise ValueError("Mapping must be a JSON object")
        if "rules" not in data:
            data["rules"] = []
        if "aliases" not in data:
            data["aliases"] = {}
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    except Exception as e:
        raise ValueError(f"Error loading mapping: {e}")


def save_mapping_json(mapping: Dict[str, Any]) -> str:
    """Convert mapping dict to JSON string"""
    return json.dumps(mapping, indent=2, ensure_ascii=False)


# ============================================================================
# MATCHING ALGORITHMS
# ============================================================================

def normalize_name(name: str) -> str:
    """Normalize name for matching: lowercase, strip whitespace, normalize punctuation"""
    if not name:
        return ""
    # Convert to lowercase, strip whitespace
    normalized = name.lower().strip()
    # Normalize common punctuation variations
    normalized = normalized.replace("_", " ").replace("-", " ")
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def exact_match(source_name: str, target_name: str) -> bool:
    """Check exact match"""
    return source_name == target_name


def case_insensitive_match(source_name: str, target_name: str) -> bool:
    """Check case-insensitive match"""
    return normalize_name(source_name) == normalize_name(target_name)


def alias_match(source_name: str, target_name: str, aliases: Dict[str, List[str]]) -> bool:
    """Check if target matches any alias of source"""
    if source_name in aliases:
        alias_list = aliases[source_name]
        normalized_target = normalize_name(target_name)
        for alias in alias_list:
            if normalize_name(alias) == normalized_target:
                return True
    return False


def regex_match(source_pattern: str, target_name: str) -> bool:
    """Check if target matches source regex pattern"""
    try:
        pattern = re.compile(source_pattern, re.IGNORECASE)
        return bool(pattern.search(target_name))
    except re.error:
        return False


def find_matching_rules(
    target_name: str,
    mapping: Dict[str, Any],
    source_keys: List[str]
) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """
    Find all mapping rules that match a target name.
    Returns list of (source_name, targets_list) tuples.
    """
    matches = []
    normalized_target = normalize_name(target_name)
    
    for rule in mapping.get("rules", []):
        # Check exact source match
        if "source" in rule:
            source_name = rule["source"]
            # Check if this rule's targets include our target
            for target in rule.get("targets", []):
                target_rule_name = target.get("name", "")
                if (exact_match(target_rule_name, target_name) or
                    case_insensitive_match(target_rule_name, target_name)):
                    matches.append((source_name, rule.get("targets", [])))
                    break
        
        # Check regex source match
        elif "source_regex" in rule:
            pattern = rule["source_regex"]
            # Check if any source key matches the regex
            for source_key in source_keys:
                if regex_match(pattern, source_key):
                    # Check if this rule's targets include our target
                    for target in rule.get("targets", []):
                        target_rule_name = target.get("name", "")
                        if (exact_match(target_rule_name, target_name) or
                            case_insensitive_match(target_rule_name, target_name)):
                            matches.append((source_key, rule.get("targets", [])))
                            break
    
    # Also check aliases
    aliases = mapping.get("aliases", {})
    for source_name, alias_list in aliases.items():
        if source_name in source_keys:
            for alias in alias_list:
                if normalize_name(alias) == normalized_target:
                    # Find rule for this source
                    for rule in mapping.get("rules", []):
                        if rule.get("source") == source_name:
                            matches.append((source_name, rule.get("targets", [])))
                            break
    
    return matches


def auto_suggest_mapping(
    source_keys: List[str],
    target_keys: List[str],
    existing_mapping: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Auto-suggest mapping based on keywords and patterns.
    Returns a mapping dict with suggested rules.
    """
    if existing_mapping is None:
        mapping = create_default_mapping()
    else:
        mapping = existing_mapping.copy()
        if "rules" not in mapping:
            mapping["rules"] = []
    
    # Phoneme mappings (Japanese to English hints)
    phoneme_hints = {
        "あ": ["aa", "ah", "AaTalk", "Aa1", "Aa"],
        "い": ["ii", "ee", "Ii", "Ee"],
        "う": ["uu", "Uu0", "Uu"],
        "え": ["ee", "Ee"],
        "お": ["oo", "Oo"],
    }
    
    # Keyword patterns
    keyword_patterns = {
        "ウィンク": ["wink", "eye_close", "Eye_Close"],
        "ウィンク右": ["wink_r", "Wink_R", "eye_close_r", "Eye_R", "R_Wink"],
        "ウィンク左": ["wink_l", "Wink_L", "eye_close_l", "Eye_L", "L_Wink"],
        "にこり": ["smile", "happy", "grin", "Smile"],
        "怒り": ["angry", "anger", "mad", "Angry"],
        "困る": ["trouble", "sad", "worried", "concerned", "Worried"],
    }
    
    suggested_rules = []
    used_targets = set()
    
    # Check existing rules to avoid duplicates
    existing_sources = set()
    for rule in mapping.get("rules", []):
        if "source" in rule:
            existing_sources.add(rule["source"])
    
    # Suggest based on phonemes
    for source_key in source_keys:
        if source_key in existing_sources:
            continue
            
        # Check phoneme hints
        if source_key in phoneme_hints:
            hints = phoneme_hints[source_key]
            for target_key in target_keys:
                normalized_target = normalize_name(target_key)
                for hint in hints:
                    if normalize_name(hint) in normalized_target or normalized_target in normalize_name(hint):
                        if target_key not in used_targets:
                            suggested_rules.append({
                                "source": source_key,
                                "targets": [{"name": target_key, "weight": 1.0}]
                            })
                            used_targets.add(target_key)
                            break
                if source_key in existing_sources:
                    break
        
        # Check keyword patterns
        for pattern_key, pattern_hints in keyword_patterns.items():
            if pattern_key in source_key or source_key in pattern_key:
                for target_key in target_keys:
                    normalized_target = normalize_name(target_key)
                    for hint in pattern_hints:
                        if normalize_name(hint) in normalized_target or normalized_target in normalize_name(hint):
                            if target_key not in used_targets:
                                suggested_rules.append({
                                    "source": source_key,
                                    "targets": [{"name": target_key, "weight": 1.0}]
                                })
                                used_targets.add(target_key)
                                break
                    if source_key in existing_sources:
                        break
                break
    
    # Add suggestions to mapping
    mapping["rules"].extend(suggested_rules)
    
    return mapping


# ============================================================================
# DRIVER SYSTEM
# ============================================================================

def create_driver_expression(
    var_name: str,
    weight: float,
    clamp_min: float,
    clamp_max: float,
    scale: float
) -> str:
    """Create driver expression string"""
    expr = f"{var_name} * {weight} * {scale}"
    
    # Add clamping
    if clamp_min != 0.0 or clamp_max != 1.0:
        expr = f"clamp({expr}, {clamp_min}, {clamp_max})"
    
    return expr


def create_shapekey_driver(
    source_obj: bpy.types.Object,
    source_key_name: str,
    target_obj: bpy.types.Object,
    target_key_name: str,
    weight: float,
    clamp_min: float,
    clamp_max: float,
    scale: float,
    direction: str
) -> bool:
    """
    Create a driver between shapekeys.
    If direction is SOURCE_TO_TARGET: target follows source
    If direction is TARGET_TO_SOURCE: source follows target
    """
    try:
        # Ensure both objects have shapekeys
        if not source_obj.data.shape_keys:
            return False
        if not target_obj.data.shape_keys:
            return False
        
        source_sk = source_obj.data.shape_keys
        target_sk = target_obj.data.shape_keys
        
        # Determine which key gets the driver and which provides the value
        if direction == "SOURCE_TO_TARGET":
            # Driver on target, value from source
            driver_key_name = target_key_name
            driver_key = target_sk.key_blocks.get(target_key_name)
            driver_sk = target_sk
            value_key_name = source_key_name
            value_sk = source_sk
        else:  # TARGET_TO_SOURCE
            # Driver on source, value from target
            driver_key_name = source_key_name
            driver_key = source_sk.key_blocks.get(source_key_name)
            driver_sk = source_sk
            value_key_name = target_key_name
            value_sk = target_sk
        
        if not driver_key:
            return False
        
        # Remove existing driver if any
        if driver_sk.animation_data:
            drivers_to_remove = []
            for driver in driver_sk.animation_data.drivers:
                if driver.data_path == f'key_blocks["{driver_key_name}"].value':
                    drivers_to_remove.append(driver)
            for driver in drivers_to_remove:
                driver_sk.animation_data.drivers.remove(driver)
        
        # Ensure animation data exists
        if not driver_sk.animation_data:
            driver_sk.animation_data_create()
        
        # Create driver
        fcurve = driver_key.driver_add("value")
        drv = fcurve.driver
        drv.type = 'SCRIPTED'
        
        # Create variable name (sanitized)
        var_name_base = f"var_{value_key_name}"
        var_name_base = var_name_base.replace(" ", "_").replace(".", "_").replace("-", "_")
        # Blender variable names have length limit and must be valid identifiers
        var_name_base = var_name_base[:60]  # Reasonable limit
        
        # Create variable
        var = drv.variables.new()
        var.name = var_name_base
        var.type = 'SINGLE_PROP'
        var.targets[0].id = value_sk
        var.targets[0].data_path = f'key_blocks["{value_key_name}"].value'
        
        # Set expression
        expr = create_driver_expression(var_name_base, weight, clamp_min, clamp_max, scale)
        drv.expression = expr
        
        return True
    except Exception as e:
        print(f"Error creating driver: {e}")
        import traceback
        traceback.print_exc()
        return False


def remove_all_drivers(obj: bpy.types.Object):
    """Remove all drivers from object's shapekeys"""
    if not obj.data.shape_keys:
        return
    
    sk = obj.data.shape_keys
    if not sk.animation_data:
        return
    
    drivers_to_remove = []
    for driver in sk.animation_data.drivers:
        drivers_to_remove.append(driver)
    
    for driver in drivers_to_remove:
        sk.animation_data.drivers.remove(driver)


# ============================================================================
# OPERATORS
# ============================================================================

class SKTM_OT_LoadPreset(Operator):
    """Load mapping preset from JSON file"""
    bl_idname = "sktm.load_preset"
    bl_label = "Load Preset JSON"
    bl_options = {'UNDO'}
    
    filepath: StringProperty(subtype='FILE_PATH')
    filter_glob: StringProperty(default='*.json', options={'HIDDEN'})
    
    def execute(self, context):
        settings = context.scene.sktm_settings
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                json_data = f.read()
            mapping = load_mapping_json(json_data)
            settings.mapping_json = save_mapping_json(mapping)
            self.report({'INFO'}, f"Loaded preset: {mapping.get('preset_name', 'Unknown')}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load preset: {e}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class SKTM_OT_SavePreset(Operator):
    """Save current mapping to JSON file"""
    bl_idname = "sktm.save_preset"
    bl_label = "Save Preset JSON"
    bl_options = {'UNDO'}
    
    filepath: StringProperty(subtype='FILE_PATH')
    filter_glob: StringProperty(default='*.json', options={'HIDDEN'})
    
    def execute(self, context):
        settings = context.scene.sktm_settings
        try:
            if not settings.mapping_json:
                # Create default if empty
                mapping = create_default_mapping()
                settings.mapping_json = save_mapping_json(mapping)
            
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.write(settings.mapping_json)
            self.report({'INFO'}, "Preset saved successfully")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to save preset: {e}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class SKTM_OT_LoadDefaultPreset(Operator):
    """Load default mapping preset"""
    bl_idname = "sktm.load_default_preset"
    bl_label = "Load Default Preset"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        settings = context.scene.sktm_settings
        mapping = create_default_mapping()
        settings.mapping_json = save_mapping_json(mapping)
        self.report({'INFO'}, "Default preset loaded")
        return {'FINISHED'}


class SKTM_OT_AutoSuggestMapping(Operator):
    """Auto-suggest mapping based on keywords and patterns"""
    bl_idname = "sktm.auto_suggest_mapping"
    bl_label = "Auto-Suggest Mapping"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        settings = context.scene.sktm_settings
        source_obj = settings.source_object
        target_obj = settings.target_object
        
        if not source_obj or not target_obj:
            self.report({'ERROR'}, "Please select source and target objects")
            return {'CANCELLED'}
        
        if not source_obj.data.shape_keys or not target_obj.data.shape_keys:
            self.report({'ERROR'}, "Both objects must have shapekeys")
            return {'CANCELLED'}
        
        source_keys = [kb.name for kb in source_obj.data.shape_keys.key_blocks if kb.name != "Basis"]
        target_keys = [kb.name for kb in target_obj.data.shape_keys.key_blocks if kb.name != "Basis"]
        
        # Load existing mapping or create new
        existing_mapping = None
        if settings.mapping_json:
            try:
                existing_mapping = load_mapping_json(settings.mapping_json)
            except:
                pass
        
        suggested_mapping = auto_suggest_mapping(source_keys, target_keys, existing_mapping)
        settings.mapping_json = save_mapping_json(suggested_mapping)
        
        self.report({'INFO'}, f"Suggested {len(suggested_mapping.get('rules', []))} mapping rules")
        return {'FINISHED'}


class SKTM_OT_ValidateMapping(Operator):
    """Validate current mapping and report issues"""
    bl_idname = "sktm.validate_mapping"
    bl_label = "Validate Mapping"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        settings = context.scene.sktm_settings
        source_obj = settings.source_object
        target_obj = settings.target_object
        
        if not source_obj or not target_obj:
            self.report({'ERROR'}, "Please select source and target objects")
            return {'CANCELLED'}
        
        if not source_obj.data.shape_keys or not target_obj.data.shape_keys:
            self.report({'ERROR'}, "Both objects must have shapekeys")
            return {'CANCELLED'}
        
        source_keys = {kb.name for kb in source_obj.data.shape_keys.key_blocks if kb.name != "Basis"}
        target_keys = {kb.name for kb in target_obj.data.shape_keys.key_blocks if kb.name != "Basis"}
        
        if not settings.mapping_json:
            self.report({'WARNING'}, "No mapping loaded. Load a preset first.")
            return {'CANCELLED'}
        
        try:
            mapping = load_mapping_json(settings.mapping_json)
        except Exception as e:
            self.report({'ERROR'}, f"Invalid mapping JSON: {e}")
            return {'CANCELLED'}
        
        issues = []
        warnings = []
        
        # Check rules
        used_sources = set()
        used_targets = set()
        
        for rule in mapping.get("rules", []):
            source_name = rule.get("source") or rule.get("source_regex", "")
            if source_name and "source_regex" not in rule:
                if source_name not in source_keys:
                    issues.append(f"Source key '{source_name}' does not exist")
            
            for target in rule.get("targets", []):
                target_name = target.get("name", "")
                if target_name:
                    used_targets.add(target_name)
                    if target_name not in target_keys:
                        issues.append(f"Target key '{target_name}' does not exist")
                    if "source" in rule:
                        used_sources.add(rule["source"])
        
        # Check for unmapped targets
        unmapped_targets = target_keys - used_targets
        if unmapped_targets:
            warnings.append(f"{len(unmapped_targets)} unmapped target keys")
        
        # Check for unused sources
        unmapped_sources = source_keys - used_sources
        if unmapped_sources:
            warnings.append(f"{len(unmapped_sources)} unused source keys")
        
        # Report
        if issues:
            self.report({'ERROR'}, f"Found {len(issues)} issues. Check console.")
            for issue in issues:
                print(f"ISSUE: {issue}")
        else:
            self.report({'INFO'}, "Mapping is valid")
        
        if warnings:
            for warning in warnings:
                print(f"WARNING: {warning}")
        
        return {'FINISHED'}


class SKTM_OT_BuildDrivers(Operator):
    """Build drivers based on current mapping"""
    bl_idname = "sktm.build_drivers"
    bl_label = "Build Drivers"
    bl_options = {'UNDO'}
    
    dry_run: BoolProperty(name="Dry Run", default=False)
    
    def execute(self, context):
        settings = context.scene.sktm_settings
        source_obj = settings.source_object
        target_obj = settings.target_object
        
        if not source_obj or not target_obj:
            self.report({'ERROR'}, "Please select source and target objects")
            return {'CANCELLED'}
        
        if not source_obj.data.shape_keys or not target_obj.data.shape_keys:
            self.report({'ERROR'}, "Both objects must have shapekeys")
            return {'CANCELLED'}
        
        if not settings.mapping_json:
            self.report({'ERROR'}, "No mapping loaded. Load a preset first.")
            return {'CANCELLED'}
        
        try:
            mapping = load_mapping_json(settings.mapping_json)
        except Exception as e:
            self.report({'ERROR'}, f"Invalid mapping JSON: {e}")
            return {'CANCELLED'}
        
        source_keys = {kb.name for kb in source_obj.data.shape_keys.key_blocks if kb.name != "Basis"}
        target_keys = {kb.name for kb in target_obj.data.shape_keys.key_blocks if kb.name != "Basis"}
        
        direction = settings.driver_direction
        clamp_min = settings.driver_clamp_min
        clamp_max = settings.driver_clamp_max
        scale = settings.driver_scale
        
        # Apply global settings from mapping if available
        if "global_settings" in mapping:
            gs = mapping["global_settings"]
            clamp_min = gs.get("clamp_min", clamp_min)
            clamp_max = gs.get("clamp_max", clamp_max)
            scale = gs.get("scale", scale)
        
        drivers_created = 0
        errors = []
        
        # Process rules
        for rule in mapping.get("rules", []):
            source_name = None
            
            if "source" in rule:
                source_name = rule["source"]
                if source_name not in source_keys:
                    continue
            elif "source_regex" in rule:
                pattern = rule["source_regex"]
                # Find matching source keys
                matching_sources = [sk for sk in source_keys if regex_match(pattern, sk)]
                if not matching_sources:
                    continue
                source_name = matching_sources[0]  # Use first match
            
            if not source_name:
                continue
            
            for target in rule.get("targets", []):
                target_name = target.get("name", "")
                weight = target.get("weight", 1.0)
                
                if target_name not in target_keys:
                    errors.append(f"Target '{target_name}' not found")
                    continue
                
                if self.dry_run:
                    print(f"Would create driver: {source_name} -> {target_name} (weight: {weight})")
                    drivers_created += 1
                else:
                    success = create_shapekey_driver(
                        source_obj, source_name,
                        target_obj, target_name,
                        weight, clamp_min, clamp_max, scale, direction
                    )
                    if success:
                        drivers_created += 1
                    else:
                        errors.append(f"Failed to create driver: {source_name} -> {target_name}")
        
        if self.dry_run:
            self.report({'INFO'}, f"Dry run: Would create {drivers_created} drivers")
        else:
            if errors:
                self.report({'WARNING'}, f"Created {drivers_created} drivers, {len(errors)} errors")
                for err in errors:
                    print(f"ERROR: {err}")
            else:
                self.report({'INFO'}, f"Created {drivers_created} drivers successfully")
        
        return {'FINISHED'}


class SKTM_OT_RemoveDrivers(Operator):
    """Remove all drivers from source and target objects"""
    bl_idname = "sktm.remove_drivers"
    bl_label = "Remove Drivers"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        settings = context.scene.sktm_settings
        source_obj = settings.source_object
        target_obj = settings.target_object
        
        removed_count = 0
        
        if source_obj and source_obj.data.shape_keys:
            remove_all_drivers(source_obj)
            removed_count += 1
        
        if target_obj and target_obj.data.shape_keys:
            remove_all_drivers(target_obj)
            removed_count += 1
        
        if removed_count == 0:
            self.report({'WARNING'}, "No objects with shapekeys selected")
        else:
            self.report({'INFO'}, f"Drivers removed from {removed_count} object(s)")
        
        return {'FINISHED'}


class SKTM_OT_BakeToAction(Operator):
    """Bake shapekey values to new action"""
    bl_idname = "sktm.bake_to_action"
    bl_label = "Bake to New Action"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        settings = context.scene.sktm_settings
        source_obj = settings.source_object
        target_obj = settings.target_object
        
        if not source_obj or not target_obj:
            self.report({'ERROR'}, "Please select source and target objects")
            return {'CANCELLED'}
        
        if not source_obj.data.shape_keys or not target_obj.data.shape_keys:
            self.report({'ERROR'}, "Both objects must have shapekeys")
            return {'CANCELLED'}
        
        if not settings.mapping_json:
            self.report({'ERROR'}, "No mapping loaded. Load a preset first.")
            return {'CANCELLED'}
        
        try:
            mapping = load_mapping_json(settings.mapping_json)
        except Exception as e:
            self.report({'ERROR'}, f"Invalid mapping JSON: {e}")
            return {'CANCELLED'}
        
        # Determine frame range
        if settings.use_scene_range:
            start_frame = context.scene.frame_start
            end_frame = context.scene.frame_end
        else:
            start_frame = settings.bake_start_frame
            end_frame = settings.bake_end_frame
        
        step = settings.bake_step
        
        # Create new action
        action_name = f"{target_obj.name}_Shapekeys_Baked"
        action = bpy.data.actions.new(name=action_name)
        
        # Get source action if exists
        source_sk = source_obj.data.shape_keys
        source_action = None
        if source_sk.animation_data and source_sk.animation_data.action:
            source_action = source_sk.animation_data.action
        
        target_sk = target_obj.data.shape_keys
        
        # Create fcurves for target shapekeys
        target_fcurves = {}
        source_keys = {kb.name: kb for kb in source_sk.key_blocks if kb.name != "Basis"}
        target_keys = {kb.name: kb for kb in target_sk.key_blocks if kb.name != "Basis"}
        
        # Build mapping dictionary for fast lookup
        mapping_dict = {}
        for rule in mapping.get("rules", []):
            source_name = rule.get("source") or rule.get("source_regex", "")
            if "source_regex" in rule:
                pattern = rule["source_regex"]
                matching_sources = [sk for sk in source_keys.keys() if regex_match(pattern, sk)]
                for ms in matching_sources:
                    if ms not in mapping_dict:
                        mapping_dict[ms] = []
                    mapping_dict[ms].extend(rule.get("targets", []))
            elif source_name:
                if source_name not in mapping_dict:
                    mapping_dict[source_name] = []
                mapping_dict[source_name].extend(rule.get("targets", []))
        
        # Create fcurves for all target keys that will be baked
        used_targets = set()
        for targets_list in mapping_dict.values():
            for target in targets_list:
                target_name = target.get("name", "")
                if target_name in target_keys and target_name not in used_targets:
                    fcurve = action.fcurves.new(
                        data_path=f'key_blocks["{target_name}"].value',
                        index=0
                    )
                    target_fcurves[target_name] = fcurve
                    used_targets.add(target_name)
        
        # Bake keyframes
        original_frame = context.scene.frame_current
        keyframes_baked = 0
        
        try:
            for frame in range(start_frame, end_frame + 1, step):
                context.scene.frame_set(frame)
                
                # Evaluate source shapekeys
                if source_action:
                    # Set source action frame
                    for fcurve in source_action.fcurves:
                        if fcurve.data_path.startswith('key_blocks['):
                            key_name = fcurve.data_path.split('"')[1]
                            if key_name in source_keys:
                                value = fcurve.evaluate(frame)
                                source_keys[key_name].value = value
                
                # Apply mapping and bake to target
                for source_name, targets_list in mapping_dict.items():
                    if source_name not in source_keys:
                        continue
                    
                    source_value = source_keys[source_name].value
                    
                    for target in targets_list:
                        target_name = target.get("name", "")
                        weight = target.get("weight", 1.0)
                        
                        if target_name in target_fcurves:
                            target_value = source_value * weight * settings.driver_scale
                            # Clamp
                            target_value = max(settings.driver_clamp_min,
                                             min(settings.driver_clamp_max, target_value))
                            
                            fcurve = target_fcurves[target_name]
                            fcurve.keyframe_points.insert(frame, target_value)
                            keyframes_baked += 1
        
        finally:
            context.scene.frame_set(original_frame)
        
        # Assign action to target
        if not target_sk.animation_data:
            target_sk.animation_data_create()
        target_sk.animation_data.action = action
        
        self.report({'INFO'}, f"Baked {keyframes_baked} keyframes to action '{action_name}'")
        return {'FINISHED'}


class SKTM_OT_ToggleLiveCopy(Operator):
    """Toggle live copy mode"""
    bl_idname = "sktm.toggle_live_copy"
    bl_label = "Toggle Live Copy"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        settings = context.scene.sktm_settings
        settings.live_copy_enabled = not settings.live_copy_enabled
        
        if settings.live_copy_enabled:
            # Register handler (avoid duplicates)
            if live_copy_handler not in bpy.app.handlers.frame_change_pre:
                bpy.app.handlers.frame_change_pre.append(live_copy_handler)
            self.report({'INFO'}, "Live copy enabled")
        else:
            # Unregister handler
            if live_copy_handler in bpy.app.handlers.frame_change_pre:
                bpy.app.handlers.frame_change_pre.remove(live_copy_handler)
            self.report({'INFO'}, "Live copy disabled")
        
        return {'FINISHED'}


# ============================================================================
# LIVE COPY HANDLER
# ============================================================================

def live_copy_handler(scene):
    """Handler for live copy mode"""
    settings = scene.sktm_settings
    
    if not settings.live_copy_enabled:
        return
    
    source_obj = settings.source_object
    target_obj = settings.target_object
    
    if not source_obj or not target_obj:
        return
    
    if not source_obj.data.shape_keys or not target_obj.data.shape_keys:
        return
    
    if not settings.mapping_json:
        return
    
    try:
        mapping = load_mapping_json(settings.mapping_json)
    except:
        return
    
    source_sk = source_obj.data.shape_keys
    target_sk = target_obj.data.shape_keys
    source_keys = {kb.name: kb for kb in source_sk.key_blocks if kb.name != "Basis"}
    target_keys = {kb.name: kb for kb in target_sk.key_blocks if kb.name != "Basis"}
    
    direction = settings.live_copy_direction
    
    # Build mapping dictionary
    mapping_dict = {}
    for rule in mapping.get("rules", []):
        source_name = rule.get("source") or rule.get("source_regex", "")
        if "source_regex" in rule:
            pattern = rule["source_regex"]
            matching_sources = [sk for sk in source_keys.keys() if regex_match(pattern, sk)]
            for ms in matching_sources:
                if ms not in mapping_dict:
                    mapping_dict[ms] = []
                mapping_dict[ms].extend(rule.get("targets", []))
        elif source_name:
            if source_name not in mapping_dict:
                mapping_dict[source_name] = []
            mapping_dict[source_name].extend(rule.get("targets", []))
    
    # Copy values
    if direction == "SOURCE_TO_TARGET":
        for source_name, targets_list in mapping_dict.items():
            if source_name not in source_keys:
                continue
            source_value = source_keys[source_name].value
            for target in targets_list:
                target_name = target.get("name", "")
                weight = target.get("weight", 1.0)
                if target_name in target_keys:
                    target_value = source_value * weight * settings.driver_scale
                    target_value = max(settings.driver_clamp_min,
                                     min(settings.driver_clamp_max, target_value))
                    target_keys[target_name].value = target_value
    else:  # TARGET_TO_SOURCE
        for source_name, targets_list in mapping_dict.items():
            if source_name not in source_keys:
                continue
            # Get first target value (or average if multiple)
            target_value = 0.0
            count = 0
            for target in targets_list:
                target_name = target.get("name", "")
                weight = target.get("weight", 1.0)
                if target_name in target_keys:
                    target_value += target_keys[target_name].value / weight
                    count += 1
            if count > 0:
                source_value = (target_value / count) / settings.driver_scale
                source_value = max(settings.driver_clamp_min,
                                 min(settings.driver_clamp_max, source_value))
                source_keys[source_name].value = source_value


# ============================================================================
# UI PANEL
# ============================================================================

class SKTM_PT_Panel(Panel):
    """Main panel for Shapekey Transfer & Mapper"""
    bl_label = "Shapekey Transfer & Mapper"
    bl_idname = "SKTM_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Face Tools"
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.sktm_settings
        
        # Initialize default mapping if empty (lazy initialization)
        if not settings.mapping_json:
            mapping = create_default_mapping()
            settings.mapping_json = save_mapping_json(mapping)
        
        # Object selection
        box = layout.box()
        box.label(text="Objects", icon='OBJECT_DATA')
        box.prop(settings, "source_object", text="Source")
        box.prop(settings, "target_object", text="Target")
        
        # Preset management
        box = layout.box()
        box.label(text="Mapping Preset", icon='FILEBROWSER')
        row = box.row()
        row.operator("sktm.load_default_preset")
        row.operator("sktm.load_preset")
        row.operator("sktm.save_preset")
        
        # Mapping tools
        box = layout.box()
        box.label(text="Mapping Tools", icon='TOOL_SETTINGS')
        box.operator("sktm.auto_suggest_mapping")
        box.operator("sktm.validate_mapping")
        
        # Transfer mode
        box = layout.box()
        box.label(text="Transfer Mode", icon='PREFERENCES')
        box.prop(settings, "transfer_mode", expand=True)
        
        # Mode-specific settings
        if settings.transfer_mode == 'DRIVER':
            box = layout.box()
            box.label(text="Driver Settings", icon='DRIVER')
            box.prop(settings, "driver_direction", expand=True)
            row = box.row()
            row.prop(settings, "driver_clamp_min")
            row.prop(settings, "driver_clamp_max")
            box.prop(settings, "driver_scale")
            
            row = box.row()
            op = row.operator("sktm.build_drivers", text="Build Drivers")
            op.dry_run = False
            row.operator("sktm.build_drivers", text="Dry Run").dry_run = True
            box.operator("sktm.remove_drivers")
        
        elif settings.transfer_mode == 'BAKE':
            box = layout.box()
            box.label(text="Bake Settings", icon='RENDER_ANIMATION')
            box.prop(settings, "use_scene_range")
            if not settings.use_scene_range:
                row = box.row()
                row.prop(settings, "bake_start_frame")
                row.prop(settings, "bake_end_frame")
            box.prop(settings, "bake_step")
            box.operator("sktm.bake_to_action")
        
        elif settings.transfer_mode == 'LIVE':
            box = layout.box()
            box.label(text="Live Copy Settings", icon='PLAY')
            box.prop(settings, "live_copy_direction", expand=True)
            box.prop(settings, "driver_clamp_min")
            box.prop(settings, "driver_clamp_max")
            box.prop(settings, "driver_scale")
            
            box.operator("sktm.toggle_live_copy")
        
        # Status info
        if settings.source_object and settings.target_object:
            box = layout.box()
            box.label(text="Status", icon='INFO')
            
            source_obj = settings.source_object
            target_obj = settings.target_object
            
            if source_obj.data.shape_keys:
                source_count = len([kb for kb in source_obj.data.shape_keys.key_blocks if kb.name != "Basis"])
                box.label(text=f"Source: {source_count} keys")
            else:
                box.label(text="Source: No shapekeys", icon='ERROR')
            
            if target_obj.data.shape_keys:
                target_count = len([kb for kb in target_obj.data.shape_keys.key_blocks if kb.name != "Basis"])
                box.label(text=f"Target: {target_count} keys")
            else:
                box.label(text="Target: No shapekeys", icon='ERROR')
            
            if settings.mapping_json:
                try:
                    mapping = load_mapping_json(settings.mapping_json)
                    rule_count = len(mapping.get("rules", []))
                    box.label(text=f"Mapping: {rule_count} rules")
                except:
                    box.label(text="Mapping: Invalid", icon='ERROR')
            else:
                box.label(text="Mapping: None loaded", icon='INFO')


# ============================================================================
# REGISTRATION
# ============================================================================

classes = (
    ShapekeyMappingRule,
    ShapekeyTransferSettings,
    SKTM_OT_LoadPreset,
    SKTM_OT_SavePreset,
    SKTM_OT_LoadDefaultPreset,
    SKTM_OT_AutoSuggestMapping,
    SKTM_OT_ValidateMapping,
    SKTM_OT_BuildDrivers,
    SKTM_OT_RemoveDrivers,
    SKTM_OT_BakeToAction,
    SKTM_OT_ToggleLiveCopy,
    SKTM_PT_Panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.sktm_settings = PointerProperty(type=ShapekeyTransferSettings)
    
    # Don't initialize here - context might not be available during installation
    # Initialization will happen when the add-on is first used


def unregister():
    # Remove live copy handler if active
    if live_copy_handler in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.remove(live_copy_handler)
    
    del bpy.types.Scene.sktm_settings
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()

