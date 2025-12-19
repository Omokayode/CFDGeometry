import os
import subprocess
import json
import time
from pathlib import Path

# ==== CONFIGURE ====
remote_host = "raj.marquette.edu"
username = "7542omokayj"
remote_base_dir = "/mmfs1/home/7542omokayj/OpenFOAM/7542omokayj-10/run"
local_base_dir = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/Research/Research_Spring25/wAB/VTKs"
ssh_key_path = os.path.expanduser("~/.ssh/rajkey")

# Sync tracking file
sync_state_file = os.path.join(local_base_dir, ".vtk_sync_state.json")

# Update mode options
UPDATE_MODES = {
    'full': 'Download everything (slow but complete)',
    'incremental': 'Only check directories modified since last sync (fast)',
    'timestamp': 'Only download files newer than local files',
    'size_check': 'Compare file sizes to detect changes'
}
# ====================

def load_sync_state():
    """Load previous sync state"""
    if os.path.exists(sync_state_file):
        try:
            with open(sync_state_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        'last_sync': 0,
        'synced_directories': {},
        'total_files': 0
    }

def save_sync_state(state):
    """Save current sync state"""
    try:
        os.makedirs(os.path.dirname(sync_state_file), exist_ok=True)
        with open(sync_state_file, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"⚠️  Could not save sync state: {e}")

def run_ssh_command(host, user, key_path, command, timeout=60):
    """Run a command on remote host via SSH"""
    ssh_cmd = [
        "ssh",
        "-i", key_path,
        "-o", "StrictHostKeyChecking=no",
        "-o", f"ConnectTimeout=30",
        f"{user}@{host}",
        command
    ]
    
    try:
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            print(f"⚠️ SSH command failed (exit code {result.returncode})")
            print(f"Command: {command}")
            print(f"Error: {result.stderr}")
            return []
        
        return result.stdout.splitlines()
    
    except subprocess.TimeoutExpired:
        print(f"⏰ SSH command timed out: {command}")
        return []
    except Exception as e:
        print(f"❌ SSH command error: {e}")
        return []

def get_directory_info(host, user, key_path, remote_dir):
    """Get directory modification time and file count"""
    # Fixed the string literal issue
    info_cmd = f"cd '{remote_dir}' && echo 'FILES:'$(ls -1 *.vtk 2>/dev/null | wc -l) && echo 'MTIME:'$(stat -c %Y . 2>/dev/null || stat -f %m . 2>/dev/null)"
    
    result = run_ssh_command(host, user, key_path, info_cmd, timeout=15)
    
    file_count = 0
    mtime = 0
    
    for line in result:
        if line.startswith("FILES:"):
            try:
                file_count = int(line.split(":")[1].strip())
            except:
                pass
        elif line.startswith("MTIME:"):
            try:
                mtime = int(line.split(":")[1].strip())
            except:
                pass
    
    return file_count, mtime

def get_vtk_files_in_dir(host, user, key_path, remote_dir):
    """Get list of VTK files in a specific directory"""
    list_cmd = f"cd '{remote_dir}' && ls -1 *.vtk 2>/dev/null || echo 'NO_VTK_FILES'"
    
    result = run_ssh_command(host, user, key_path, list_cmd, timeout=30)
    
    vtk_files = []
    for line in result:
        line = line.strip()
        if line and line.endswith('.vtk') and 'NO_VTK_FILES' not in line:
            vtk_files.append(line)
    
    return vtk_files

def check_directory_needs_update(host, user, key_path, remote_dir, sync_state, mode='incremental'):
    """Check if directory needs updating based on chosen mode"""
    
    if mode == 'full':
        return True, "Full sync mode"
    
    rel_path = os.path.relpath(remote_dir, remote_base_dir)
    
    # Get current directory info
    file_count, mtime = get_directory_info(host, user, key_path, remote_dir)
    
    if file_count == 0:
        return False, "No VTK files"
    
    # Check against previous sync state
    dir_key = rel_path
    previous_info = sync_state['synced_directories'].get(dir_key, {})
    
    if mode == 'incremental':
        # Check if directory was modified since last sync
        last_sync_time = sync_state.get('last_sync', 0)
        if mtime > last_sync_time:
            return True, f"Modified since last sync ({time.ctime(mtime)})"
        
        # Check if file count changed
        prev_count = previous_info.get('file_count', 0)
        if file_count != prev_count:
            return True, f"File count changed: {prev_count} → {file_count}"
        
        return False, "Already up to date"
    
    elif mode == 'size_check':
        # Compare with local directory
        local_dir = os.path.join(local_base_dir, rel_path)
        if not os.path.exists(local_dir):
            return True, "Local directory doesn't exist"
        
        local_vtk_count = len([f for f in os.listdir(local_dir) if f.endswith('.vtk')])
        if local_vtk_count != file_count:
            return True, f"File count mismatch: local={local_vtk_count}, remote={file_count}"
        
        return False, "File counts match"
    
    return True, "Unknown mode"

def filter_directories_for_update(host, user, key_path, directories, sync_state, mode='incremental'):
    """Filter directories that need updating"""
    
    if mode == 'full':
        print("🔄 Full sync mode - will process all directories")
        return directories
    
    print(f"🔍 Checking {len(directories)} directories for updates using '{mode}' mode...")
    
    directories_to_update = []
    up_to_date_count = 0
    
    for i, remote_dir in enumerate(directories, 1):
        if i % 20 == 0:
            print(f"   📊 Checked {i}/{len(directories)} directories...")
        
        needs_update, reason = check_directory_needs_update(host, user, key_path, remote_dir, sync_state, mode)
        
        if needs_update:
            directories_to_update.append(remote_dir)
            rel_path = os.path.relpath(remote_dir, remote_base_dir)
            print(f"   📁 Will update: {rel_path} ({reason})")
        else:
            up_to_date_count += 1
    
    print(f"✅ Update check complete:")
    print(f"   📥 {len(directories_to_update)} directories need updating")
    print(f"   ✅ {up_to_date_count} directories already up to date")
    
    return directories_to_update

def download_directory_with_scp(host, user, key_path, remote_dir, local_dir):
    """Download entire directory using SCP"""
    print(f"📂 Downloading entire directory: {remote_dir}")
    
    # Create local directory
    os.makedirs(local_dir, exist_ok=True)
    
    # Use SCP to copy all VTK files from the directory
    scp_cmd = [
        "scp",
        "-i", key_path,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=30",
        f"{user}@{host}:{remote_dir}/*.vtk",
        local_dir + "/"
    ]
    
    try:
        result = subprocess.run(
            scp_cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode == 0:
            print(f"✅ Directory download successful")
            return True
        else:
            # If wildcard fails, try individual files
            print(f"⚠️ Wildcard SCP failed, trying individual files...")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ SCP timeout for directory {remote_dir}")
        return False
    except Exception as e:
        print(f"❌ SCP error: {e}")
        return False

def download_individual_files(host, user, key_path, remote_dir, local_dir):
    """Download VTK files individually"""
    vtk_files = get_vtk_files_in_dir(host, user, key_path, remote_dir)
    
    if not vtk_files:
        print(f"📭 No VTK files found in {remote_dir}")
        return {
            'success': True,
            'file_count': 0,
            'downloaded': 0
        }
    
    print(f"📄 Found {len(vtk_files)} VTK files, downloading individually...")
    
    downloaded = 0
    skipped = 0
    errors = 0
    
    for filename in vtk_files:
        local_path = os.path.join(local_dir, filename)
        remote_path = os.path.join(remote_dir, filename)
        
        # Skip if file already exists and has content
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            print(f"⏩ Skipping existing: {filename}")
            skipped += 1
            continue
        
        print(f"⬇️  Downloading {filename}...")
        
        scp_cmd = [
            "scp",
            "-i", key_path,
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=30",
            f"{user}@{host}:{remote_path}",
            local_path
        ]
        
        try:
            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                downloaded += 1
                print(f"   ✅ Downloaded successfully")
            else:
                errors += 1
                print(f"   ❌ Failed: {result.stderr}")
                
        except Exception as e:
            errors += 1
            print(f"   ❌ Error: {e}")
    
    print(f"📊 Summary: {downloaded} downloaded, {skipped} skipped, {errors} errors")
    
    # Return success info for sync state tracking
    return {
        'success': errors == 0,
        'file_count': len(vtk_files),
        'downloaded': downloaded
    }

def discover_vtk_directories_efficiently(host, user, key_path, base_dir):
    """Efficiently discover all directories containing VTK files"""
    print(f"🔍 Discovering VTK directories in {base_dir}")
    
    # Use a more efficient approach: find all .vtk files, then extract unique directories
    # This command gets all VTK files and extracts their directories in one go
    find_cmd = f"cd '{base_dir}' && find . -name '*.vtk' -type f | sed 's|/[^/]*$||' | sort -u"
    
    print("⏳ Running directory discovery (this may take a moment)...")
    relative_dirs = run_ssh_command(host, user, key_path, find_cmd, timeout=180)
    
    if not relative_dirs:
        print("❌ No VTK directories found")
        return []
    
    # Convert to absolute paths and filter
    absolute_dirs = []
    for rel_dir in relative_dirs:
        rel_dir = rel_dir.strip()
        if not rel_dir or rel_dir == '.':
            continue
            
        if rel_dir.startswith('./'):
            abs_dir = os.path.join(base_dir, rel_dir[2:])
        else:
            abs_dir = os.path.join(base_dir, rel_dir)
        
        absolute_dirs.append(abs_dir)
    
    print(f"✅ Found {len(absolute_dirs)} directories containing VTK files")
    
    # Show first few directories as preview
    if absolute_dirs:
        print("📋 Preview of directories:")
        for i, dir_path in enumerate(absolute_dirs[:10]):
            rel_path = os.path.relpath(dir_path, base_dir)
            print(f"   📁 {rel_path}")
        if len(absolute_dirs) > 10:
            print(f"   ... and {len(absolute_dirs) - 10} more directories")
    
    return absolute_dirs

def choose_update_mode():
    """Let user choose update mode"""
    print("\n🔧 Choose update mode:")
    for i, (mode, description) in enumerate(UPDATE_MODES.items(), 1):
        print(f"   {i}. {mode}: {description}")
    
    while True:
        try:
            choice = input(f"\nEnter choice (1-{len(UPDATE_MODES)}) or press Enter for incremental: ").strip()
            
            if not choice:
                return 'incremental'
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(UPDATE_MODES):
                return list(UPDATE_MODES.keys())[choice_num - 1]
            else:
                print("❌ Invalid choice, please try again")
        except ValueError:
            print("❌ Please enter a number")
        except KeyboardInterrupt:
            print("\n❌ Cancelled by user")
            return None

def update_sync_state_for_directory(sync_state, remote_dir, file_count, mtime):
    """Update sync state for a successfully processed directory"""
    rel_path = os.path.relpath(remote_dir, remote_base_dir)
    sync_state['synced_directories'][rel_path] = {
        'file_count': file_count,
        'mtime': mtime,
        'last_synced': int(time.time())
    }

def test_ssh_connection(host, user, key_path):
    """Test SSH connection"""
    print(f"🔍 Testing SSH connection to {user}@{host}")
    
    test_result = run_ssh_command(host, user, key_path, "echo 'SSH connection successful'", timeout=15)
    
    if test_result and "SSH connection successful" in test_result[0]:
        print("✅ SSH connection test passed")
        return True
    else:
        print("❌ SSH connection test failed")
        return False

def main():
    """Main execution function"""
    print("🚀 Starting VTK file download process")
    
    # Check if SSH key exists
    if not os.path.exists(ssh_key_path):
        print(f"❌ SSH key not found: {ssh_key_path}")
        return
    
    # Test SSH connection first
    if not test_ssh_connection(remote_host, username, ssh_key_path):
        print("💡 Troubleshooting tips:")
        print("   - Ensure SSH key is correct and has proper permissions (chmod 600)")
        print("   - Try connecting manually: ssh -i ~/.ssh/rajkey 7542omokayj@raj.marquette.edu")
        return
    
    try:
        # Load previous sync state
        sync_state = load_sync_state()
        last_sync = sync_state.get('last_sync', 0)
        if last_sync > 0:
            print(f"📅 Last sync: {time.ctime(last_sync)}")
            print(f"📁 Previously synced: {len(sync_state.get('synced_directories', {}))} directories")
        else:
            print("📅 No previous sync found - this will be a full sync")
        
        # Choose update mode
        update_mode = choose_update_mode()
        if not update_mode:
            return
        
        print(f"\n🔧 Using update mode: {update_mode}")
        
        # Use efficient auto-discovery to find all VTK directories
        print("\n🔍 Auto-discovering all VTK directories...")
        all_directories = discover_vtk_directories_efficiently(remote_host, username, ssh_key_path, remote_base_dir)
        
        if not all_directories:
            print("❌ No VTK directories found")
            return
        
        # Filter directories that need updating
        directories_to_process = filter_directories_for_update(
            remote_host, username, ssh_key_path, all_directories, sync_state, update_mode
        )
        
        if not directories_to_process:
            print("🎉 All directories are already up to date!")
            return
        
        print(f"\n📋 Will process {len(directories_to_process)} directories")
        
        # Ask user if they want to proceed
        if len(directories_to_process) > 10:
            response = input(f"\n❓ Proceed with downloading {len(directories_to_process)} directories? (y/n): ")
            if response.lower() not in ['y', 'yes']:
                print("❌ Download cancelled by user")
                return
        
        # Download files from each directory with progress tracking
        successful_dirs = 0
        failed_dirs = 0
        total_files_downloaded = 0
        
        for i, remote_dir in enumerate(directories_to_process, 1):
            print(f"\n📂 Processing directory {i}/{len(directories_to_process)}")
            
            # Calculate relative path for local storage
            rel_path = os.path.relpath(remote_dir, remote_base_dir)
            local_dir = os.path.join(local_base_dir, rel_path)
            
            print(f"   Remote: {rel_path}")
            print(f"   Local:  {local_dir}")
            
            # Get directory info for sync state tracking
            file_count, mtime = get_directory_info(remote_host, username, ssh_key_path, remote_dir)
            
            # Try directory download first, fallback to individual files
            download_success = False
            try:
                if download_directory_with_scp(remote_host, username, ssh_key_path, remote_dir, local_dir):
                    download_success = True
                    successful_dirs += 1
                    total_files_downloaded += file_count
                else:
                    print("   🔄 Retrying with individual file downloads...")
                    result = download_individual_files(remote_host, username, ssh_key_path, remote_dir, local_dir)
                    if result and result.get('success', False):
                        download_success = True
                        successful_dirs += 1
                        total_files_downloaded += result.get('downloaded', 0)
                    else:
                        failed_dirs += 1
            except Exception as e:
                print(f"   ❌ Error processing directory: {e}")
                failed_dirs += 1
            
            # Update sync state for successful downloads
            if download_success:
                update_sync_state_for_directory(sync_state, remote_dir, file_count, mtime)
            
            # Save sync state periodically
            if i % 10 == 0:
                sync_state['last_sync'] = int(time.time())
                save_sync_state(sync_state)
                print(f"   💾 Sync state saved (checkpoint)")
            
            # Show progress
            if i % 5 == 0 or i == len(directories_to_process):
                print(f"   📊 Progress: {i}/{len(directories_to_process)} directories processed")
        
        # Final sync state update
        sync_state['last_sync'] = int(time.time())
        sync_state['total_files'] = sync_state.get('total_files', 0) + total_files_downloaded
        save_sync_state(sync_state)
        
        print(f"\n🎉 Download process completed!")
        print(f"📊 Final summary:")
        print(f"   ✅ {successful_dirs} directories successful")
        print(f"   ❌ {failed_dirs} directories failed")
        print(f"   📄 {total_files_downloaded} files downloaded")
        print(f"   💾 Sync state saved to: {sync_state_file}")
        
        if failed_dirs > 0:
            print(f"⚠️  {failed_dirs} directories had issues - you may want to retry those manually")
        
    except KeyboardInterrupt:
        print("\n⏹️  Download interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")

if __name__ == "__main__":
    main()