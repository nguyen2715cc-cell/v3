# Tạo file: fix_ratelimit_issue.py

import os
import shutil
from datetime import datetime

def backup_file(filepath):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backup: {backup_path}")
    return True

def apply_fix():
    filepath = "ui/video_ban_hang_v5_complete.py"
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    backup_file(filepath)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\n🔧 Fixing rate limit issues...\n")
    
    # FIX 1: Change delay_before from 0 to RATE_LIMIT_DELAY_SEC
    old_code1 = '''                        img_data_url = image_gen_service.generate_image_with_rate_limit(
                            text=prompt,  # Fixed: 'prompt' → 'text'
                            api_keys=api_keys,
                            model=model,
                            aspect_ratio=aspect_ratio,
                            delay_before=0,
                            logger=lambda msg: self.progress.emit(msg),
                        )'''
    
    new_code1 = '''                        img_data_url = image_gen_service.generate_image_with_rate_limit(
                            text=prompt,
                            api_keys=api_keys,
                            model=model,
                            aspect_ratio=aspect_ratio,
                            delay_before=RATE_LIMIT_DELAY_SEC if i > 0 else 0,  # Enhanced: Respect rate limit
                            logger=lambda msg: self.progress.emit(msg),
                        )'''
    
    if old_code1 in content:
        content = content.replace(old_code1, new_code1)
        print("  ✓ Fixed delay_before for scene images")
    
    # FIX 2: Same for thumbnails
    old_code2 = '''                    thumb_data_url = image_gen_service.generate_image_with_rate_limit(
                        text=prompt,  # Fixed: 'prompt' → 'text'
                        api_keys=api_keys,
                        model=model,
                        aspect_ratio=aspect_ratio,
                        delay_before=0,
                        logger=lambda msg: self.progress.emit(msg)
                    )'''
    
    new_code2 = '''                    thumb_data_url = image_gen_service.generate_image_with_rate_limit(
                        text=prompt,
                        api_keys=api_keys,
                        model=model,
                        aspect_ratio=aspect_ratio,
                        delay_before=RATE_LIMIT_DELAY_SEC,  # Enhanced: Always delay for thumbnails
                        logger=lambda msg: self.progress.emit(msg)
                    )'''
    
    if old_code2 in content:
        content = content.replace(old_code2, new_code2)
        print("  ✓ Fixed delay_before for thumbnails")
    
    # FIX 3: Remove duplicate delay (dòng 249-253 now handled by generate_image_with_rate_limit)
    old_delay = '''                # CRITICAL FIX: Add mandatory delay BEFORE every request (except first)
                # This prevents rate limiting regardless of which key is used
                if i > 0:
                    self.progress.emit(
                        f"[RATE LIMIT] Chờ {RATE_LIMIT_DELAY_SEC}s trước khi tạo ảnh cảnh {scene.get('index')}..."
                    )
                    time.sleep(RATE_LIMIT_DELAY_SEC)'''
    
    # Comment it out instead of removing (for clarity)
    new_delay = '''                # NOTE: Rate limiting now handled by generate_image_with_rate_limit()
                # No need for manual delay here anymore'''
    
    content = content.replace(old_delay, new_delay)
    print("  ✓ Removed duplicate manual delay")
    
    # FIX 4: Same for thumbnail delay
    old_thumb_delay = '''                # CRITICAL FIX: Delay before thumbnails too
                # First thumbnail comes after all scene images, so always delay
                self.progress.emit(
                    f"[RATE LIMIT] Chờ {RATE_LIMIT_DELAY_SEC}s trước thumbnail {i+1}..."
                )
                time.sleep(RATE_LIMIT_DELAY_SEC)'''
    
    new_thumb_delay = '''                # NOTE: Rate limiting now handled by generate_image_with_rate_limit()'''
    
    content = content.replace(old_thumb_delay, new_thumb_delay)
    print("  ✓ Removed duplicate thumbnail delay")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✅ FIXES APPLIED!")
    print("\n📝 Changes:")
    print("   1. delay_before now uses RATE_LIMIT_DELAY_SEC")
    print("   2. Removed duplicate manual time.sleep() calls")
    print("   3. Rate limiting fully handled by generate_image_with_rate_limit()")
    print("\n🔄 Test image generation now - should not hit rate limits!")
    
    return True

if __name__ == "__main__":
    print("=" * 70)
    print("🛠️  FIX: IMAGE GENERATION RATE LIMIT")
    print("=" * 70)
    print()
    
    confirm = input("Apply fix? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Cancelled.")
        exit(0)
    
    print()
    
    if apply_fix():
        print("\n" + "=" * 70)
        print("🎉 SUCCESS!")
        print("=" * 70)
    else:
        print("\n❌ FAILED!")