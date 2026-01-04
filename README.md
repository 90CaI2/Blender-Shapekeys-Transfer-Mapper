# Blender-Shapekeys-Transfer-Mapper
Blender 4.5 add-on for transferring and mapping shapekeys between MMD and custom facial systems with flexible JSON-based mapping rules, driver creation, and baking support.


# Shapekey Transfer & Mapper

A Blender 4.5.5 LTS add-on for transferring and mapping shapekeys between SOURCE (MMD) and TARGET meshes with flexible mapping rules.

## Installation

### Option 1: Install Single File (Current Method)
1. In Blender: Edit > Preferences > Add-ons > Install...
2. Navigate to and select `shapekey_transfer_mapper.py`
3. Enable the add-on: Search for "Shapekey Transfer & Mapper" and check the box

### Option 2: Package as ZIP (Recommended for Distribution)
1. Create a folder named `shapekey_transfer_mapper` (must match the add-on name)
2. Place `shapekey_transfer_mapper.py` inside this folder
3. Optionally include `mapping_preset_mmd_to_face.json` and `README.md`
4. Zip the folder (not its contents)
5. In Blender: Edit > Preferences > Add-ons > Install... > Select the `.zip` file
6. Enable the add-on

**Note**: The JSON preset file can be loaded separately using the "Load Preset JSON" button in the add-on panel, so it doesn't need to be in the zip unless you want to distribute it together.

## Usage

### Accessing the Panel

Open the 3D Viewport and press `N` to open the sidebar. Navigate to the "Face Tools" tab.

### Basic Workflow

1. **Select Objects**: Choose your SOURCE (MMD mesh) and TARGET (your facial system) objects
2. **Load Mapping**: 
   - Click "Load Default Preset" to use the built-in MMD-to-Face mapping
   - Or click "Load Preset JSON" to load your custom mapping file
3. **Validate**: Click "Validate Mapping" to check for issues
4. **Auto-Suggest** (optional): Click "Auto-Suggest Mapping" to get intelligent suggestions
5. **Choose Mode**: Select Driver, Bake, or Live Copy mode
6. **Execute**: Build drivers, bake to action, or enable live copy

## JSON Mapping Format

The mapping system uses JSON files to define how SOURCE shapekeys map to TARGET shapekeys.

### Basic Structure

```json
{
  "preset_name": "MMD_to_Fac_v1",
  "direction_default": "SOURCE_TO_TARGET",
  "rules": [
    {
      "source": "あ",
      "targets": [
        {"name": "Fac_Mth_AaTalk", "weight": 1.0}
      ]
    }
  ],
  "aliases": {
    "あ": ["aa", "ah", "AaTalk"]
  },
  "global_settings": {
    "clamp_min": 0.0,
    "clamp_max": 1.0,
    "scale": 1.0
  }
}
```

### Rule Types

#### 1. Direct Source Mapping
```json
{
  "source": "ウィンク右",
  "targets": [
    {"name": "Fac_Eye_R_Wink", "weight": 1.0}
  ]
}
```

#### 2. One Source to Multiple Targets
```json
{
  "source": "ウィンク右",
  "targets": [
    {"name": "Fac_Eye_R_Wink", "weight": 1.0},
    {"name": "Fac_Eye_R_HalfClose", "weight": 0.3}
  ]
}
```

#### 3. Regex Pattern Matching
```json
{
  "source_regex": "ウィンク.*右|wink.*r",
  "targets": [
    {"name": "Fac_Eye_R_Wink", "weight": 1.0}
  ]
}
```

### Aliases

Aliases help match variations of names:
```json
{
  "aliases": {
    "怒り": ["angry", "anger", "mad"],
    "困る": ["trouble", "sad", "worried"]
  }
}
```

### Global Settings

Apply default clamp and scale values:
```json
{
  "global_settings": {
    "clamp_min": 0.0,
    "clamp_max": 1.0,
    "scale": 1.0
  }
}
```

## Transfer Modes

### Driver Mode (Recommended)

Creates Blender drivers that link shapekey values. Drivers persist in the .blend file and work with animation.

**Directions:**
- **SOURCE → TARGET**: Play MMD morph animation, target reproduces it
- **TARGET → SOURCE**: Animate target keys, source responds

**Settings:**
- Clamp Min/Max: Limit the output value range
- Scale: Multiply the value

**Operations:**
- **Build Drivers**: Create drivers based on current mapping
- **Dry Run**: Preview what would be created without making changes
- **Remove Drivers**: Remove all drivers from both objects

### Bake Mode

Converts an existing Action on SOURCE shapekeys and bakes keyframes onto TARGET shapekeys.

**Settings:**
- Use Scene Range: Use scene's frame range
- Start/End Frame: Custom frame range
- Step: Sample every N frames (default: 1)

**Operation:**
- **Bake to New Action**: Creates a new action on the TARGET object

### Live Copy Mode

Copies values on every frame update without creating drivers. Useful as a fallback when drivers are undesirable.

**Settings:**
- Copy Direction: SOURCE → TARGET or TARGET → SOURCE
- Clamp/Scale: Same as Driver Mode

**Operation:**
- **Toggle Live Copy**: Enable/disable the live copy handler

## Features

### Auto-Suggest Mapping

Intelligently suggests mappings based on:
- Japanese phonemes (あ/い/う/え/お) → English equivalents
- Keyword patterns (ウィンク → wink, にこり → smile, etc.)
- Case-insensitive matching
- Partial name matching

### Validation

Checks for:
- Missing source keys
- Missing target keys
- Invalid JSON structure
- Unmapped keys (warnings)

### Safety Features

- **Dry Run**: Preview changes before applying
- **Undo-Safe**: All operations support Blender's undo system
- **Non-Destructive**: Never renames existing shapekeys
- **Error Reporting**: Clear error messages in the UI

## Tips

1. **Start with Default Preset**: The default preset covers common MMD shapekeys
2. **Use Auto-Suggest**: Let the system suggest mappings, then refine manually
3. **Validate First**: Always validate before building drivers or baking
4. **Save Presets**: Save your custom mappings for reuse
5. **Driver Mode for Animation**: Use Driver Mode for animated workflows
6. **Bake for Export**: Use Bake Mode when you need a final action without drivers

## Troubleshooting

### Finding the Add-on

If you can't find the add-on in the list:
1. Search for: **"Shapekey"**, **"Transfer"**, or **"Mapper"**
2. Look in the **"Animation"** category
3. Make sure the add-on is enabled (checkbox should be checked)
4. If still not found, try:
   - Disable and re-enable the add-on
   - Restart Blender
   - Reinstall the add-on

### Common Issues

**"No mapping loaded"**: Load a preset first (default or custom)

**"Both objects must have shapekeys"**: Ensure both meshes have shape keys created

**Drivers not working**: Check that both objects have shapekeys and the mapping is valid

**Live copy not updating**: Ensure Live Copy is enabled and the handler is registered

**Icon errors**: If you see icon-related errors:
1. **Disable** the add-on
2. **Delete** the old add-on file from: `C:\Users\[YourName]\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\addons\`
3. **Reinstall** the add-on (install the updated .py file)
4. **Enable** the add-on again

**Add-on not updating after changes**: 
- Blender caches add-ons. After updating the file:
  1. Go to Edit > Preferences > Add-ons
  2. Disable the add-on (uncheck the box)
  3. Enable it again (check the box)
  4. Or restart Blender completely

## Technical Notes

- Drivers use Blender's `SINGLE_PROP` variable type
- Expressions support clamping and scaling
- Variable names are sanitized to valid Blender identifiers
- Frame change handler is automatically registered/unregistered for Live Copy mode

## License

This add-on is provided as-is for use with Blender 4.5.5 LTS.

