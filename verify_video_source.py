#!/usr/bin/env python3
"""
Video Source Verification Script

This script verifies if a video file came from Google Labs API or was generated locally.
It checks:
1. If operation_name exists in Google Labs
2. If video URL matches Google's domain
3. ProjectID ownership verification
"""

import os
import sys
import json
import argparse
import requests
from typing import Optional


def verify_video_is_real(video_path: str, operation_name: Optional[str] = None, 
                         token: Optional[str] = None, project_id: Optional[str] = None) -> dict:
    """
    Verify if a video file came from Google Labs API
    
    Args:
        video_path: Path to the video file to verify
        operation_name: Google Labs operation name (if known)
        token: Google Labs bearer token for API access
        project_id: Project ID to verify ownership
    
    Returns:
        dict with verification results
    """
    results = {
        'video_exists': False,
        'file_size': 0,
        'is_valid_mp4': False,
        'operation_verified': False,
        'api_accessible': False,
        'project_id_matches': None,
        'video_url_domain': None,
        'errors': []
    }
    
    # Check 1: Video file exists locally
    print(f"\n{'='*60}")
    print(f"VERIFICATION REPORT: {os.path.basename(video_path)}")
    print(f"{'='*60}\n")
    
    if os.path.exists(video_path):
        results['video_exists'] = True
        results['file_size'] = os.path.getsize(video_path)
        print(f"✓ Video file exists: {video_path}")
        print(f"  File size: {results['file_size'] / 1024 / 1024:.2f} MB")
    else:
        results['errors'].append("Video file not found")
        print(f"✗ Video file not found: {video_path}")
        return results
    
    # Check 2: Verify MP4 signature
    try:
        with open(video_path, 'rb') as f:
            header = f.read(12)
            # MP4 files have 'ftyp' at offset 4
            if header[4:8] == b'ftyp':
                results['is_valid_mp4'] = True
                print(f"✓ Valid MP4 file signature detected")
            else:
                print(f"✗ Invalid MP4 signature (file may be corrupted or fake)")
                results['errors'].append("Invalid MP4 signature")
    except Exception as e:
        results['errors'].append(f"Error reading file: {e}")
        print(f"✗ Error reading file: {e}")
    
    # Check 3: Verify operation with Google Labs API (if credentials provided)
    if operation_name and token:
        print(f"\n--- API Verification ---")
        print(f"Operation Name: {operation_name[:50]}...")
        print(f"Project ID: {project_id or 'NOT PROVIDED'}")
        
        try:
            # Call Google Labs API to check operation status
            url = "https://aisandbox-pa.googleapis.com/v1/video:batchCheckAsyncVideoGenerationStatus"
            headers = {
                "authorization": f"Bearer {token}",
                "content-type": "application/json; charset=utf-8",
                "origin": "https://labs.google",
                "referer": "https://labs.google/",
            }
            payload = {
                "operations": [
                    {"operation": {"name": operation_name}}
                ]
            }
            
            print(f"Calling API: {url}")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                results['api_accessible'] = True
                print(f"✓ API accessible (HTTP 200)")
                
                data = response.json()
                operations = data.get("operations", [])
                
                if operations:
                    results['operation_verified'] = True
                    op = operations[0]
                    print(f"✓ Operation found in Google Labs")
                    
                    # Extract video URL
                    response_data = op.get("response", {})
                    
                    # Try multiple possible URL locations
                    video_url = None
                    for key_path in [
                        ("operation", "metadata", "video", "fifeUrl"),
                        ("video", "url"),
                        ("downloadUrl",),
                    ]:
                        obj = response_data
                        for key in key_path:
                            obj = obj.get(key, {}) if isinstance(obj, dict) else {}
                        if isinstance(obj, str) and obj.startswith("http"):
                            video_url = obj
                            break
                    
                    if video_url:
                        results['video_url_domain'] = video_url.split('/')[2] if '://' in video_url else None
                        print(f"✓ Video URL found: {video_url[:80]}...")
                        print(f"  Domain: {results['video_url_domain']}")
                        
                        # Verify it's a Google domain
                        if results['video_url_domain'] and 'google' in results['video_url_domain'].lower():
                            print(f"✓ URL is from Google domain")
                        else:
                            print(f"⚠ URL is NOT from Google domain (suspicious!)")
                            results['errors'].append("Video URL is not from Google domain")
                    else:
                        print(f"✗ No video URL found in operation response")
                        results['errors'].append("No video URL in operation")
                    
                    # Check project ID
                    op_metadata = op.get("operation", {}).get("metadata", {})
                    op_project_id = op_metadata.get("projectId")
                    
                    if project_id:
                        if op_project_id == project_id:
                            results['project_id_matches'] = True
                            print(f"✓ Project ID matches ({project_id})")
                        else:
                            results['project_id_matches'] = False
                            print(f"✗ Project ID MISMATCH!")
                            print(f"  Expected: {project_id}")
                            print(f"  Found: {op_project_id or 'NONE'}")
                            results['errors'].append(f"Project ID mismatch: expected {project_id}, got {op_project_id}")
                else:
                    print(f"✗ Operation NOT found in Google Labs (may be expired or invalid)")
                    results['errors'].append("Operation not found in API response")
            else:
                print(f"✗ API error: HTTP {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                results['errors'].append(f"API HTTP {response.status_code}")
        except Exception as e:
            print(f"✗ API verification failed: {e}")
            results['errors'].append(f"API error: {e}")
    else:
        print(f"\n⚠ API verification skipped (no operation_name or token provided)")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY:")
    print(f"{'='*60}")
    
    if results['video_exists'] and results['is_valid_mp4']:
        if results['operation_verified']:
            print("✓ Video appears to be from Google Labs API")
            if results['project_id_matches'] is False:
                print("⚠ WARNING: Video is in WRONG project!")
                print("  This explains why it doesn't appear in your Google Labs UI")
        else:
            print("⚠ Cannot verify if video is from Google Labs")
            print("  (Provide operation_name and token for verification)")
    else:
        print("✗ Video file has issues")
    
    if results['errors']:
        print(f"\nErrors detected ({len(results['errors'])}):")
        for err in results['errors']:
            print(f"  - {err}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Verify video source from Google Labs API")
    parser.add_argument("video_path", help="Path to video file to verify")
    parser.add_argument("--operation-name", help="Google Labs operation name")
    parser.add_argument("--token", help="Google Labs bearer token")
    parser.add_argument("--project-id", help="Expected project ID")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    results = verify_video_is_real(
        args.video_path,
        operation_name=args.operation_name,
        token=args.token,
        project_id=args.project_id
    )
    
    if args.json:
        print("\n" + json.dumps(results, indent=2))
    
    # Exit code based on results
    if results['errors']:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
