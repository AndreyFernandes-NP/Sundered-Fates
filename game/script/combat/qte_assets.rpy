################################################################################
## QTE ASSETS
##
## Finds the images that belong to a QTE animation and puts them in order
## basically, we give it a path like "images/combat/dummy/dummy_up" and it
## looks for dummy_up.png, dummy_up2.png, dummy_up3.png and so on.
## This is just a setup for the image list, everything else is handled by qte_visuals
################################################################################

init -10 python:
    
    def qte_get_frames(base_path: str):
        frames_by_number = {}
        extensions = [".png", ".jpg", ".jpeg", ".gif"]

        for file_path in renpy.list_files():
            if "." not in file_path:
                continue

            name, ext = file_path.rsplit(".", 1)

            # Check if the file path starts with the base path and has a valid extension
            if ext.lower() not in [e[1:] for e in extensions]:
                continue
            
            if not name.startswith(base_path):
                continue

            # Keep only the part after the requested animation name
            # 'dummy_up3.png' turns into '3' as an example.
            suffix = name[len(base_path):]

            if suffix == "":
                frame_number = 1
            
            elif suffix.isdecimal():
                frame_number = int(suffix)
            
            else:
                # Something like "_attack" belongs to another animation and not this
                continue
            
            # Check if the frame number is valid and not already in the list
            if frame_number < 1:
                if config.developer:
                    renpy.log(f"QTE: Ignoring frame {file_path} because its number is less than 1.")

                continue

            # Also check if the frame number is already in the list to avoid duplicates in any case
            if frame_number in frames_by_number:
                if config.developer:
                    renpy.log(f"QTE: Ignoring frame {file_path} because its number is already in the list.")

                continue

            frames_by_number[frame_number] = file_path
        
        if not frames_by_number:
            if config.developer:
                renpy.log(f"QTE: No frames found for base path '{base_path}'.")
            
            return {}
        
        frames = []

        for frame_number in sorted(frames_by_number.keys()):
            frames.append(frames_by_number[frame_number])
        
        if config.developer:
            renpy.log(f"QTE: Found {len(frames)} frames for base path '{base_path}': {frames}")
        
        return frames
