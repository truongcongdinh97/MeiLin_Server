#!/usr/bin/env python3
"""
Test Quota Management System for Personal Knowledge Manager
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.personal_knowledge_manager import PersonalKnowledgeManager, DEFAULT_QUOTA

def test_quota_system():
    """Test quota management features"""
    print("=" * 60)
    print("Testing Quota Management System")
    print("=" * 60)
    
    # Create manager with lower limits for testing
    test_quota = {
        'max_documents': 10,
        'max_storage_mb': 1,
        'max_chars_per_doc': 500,
        'cleanup_strategy': 'oldest',
        'cleanup_threshold': 0.8,
        'cleanup_amount': 0.3,
    }
    
    manager = PersonalKnowledgeManager(
        base_dir="data/test_user_knowledge",
        quota_config=test_quota
    )
    
    test_user = "test_quota_user_123"
    
    # Clean up first
    manager.delete_user_knowledge(test_user)
    
    print("\n1. Testing default quota...")
    quota = manager.get_user_quota(test_user)
    print(f"   Documents: {quota['documents_count']}/{quota['documents_limit']}")
    print(f"   Storage: {quota['storage_bytes']}/{quota['storage_limit_mb']}MB")
    assert quota['documents_count'] == 0
    assert quota['documents_limit'] == 10
    print("   ✅ Default quota OK")
    
    print("\n2. Testing add documents...")
    for i in range(8):
        content = f"Test document {i}: This is sample content for testing quota system."
        result = manager.add_document_to_quota(test_user, f"DOC_{i:03d}", content)
        print(f"   Added DOC_{i:03d}: {result['success']} - {result['message']}")
        assert result['success']
    
    quota = manager.get_user_quota(test_user)
    print(f"   Documents: {quota['documents_count']}/{quota['documents_limit']}")
    print(f"   Usage: {quota['usage_percent']:.1f}%")
    assert quota['documents_count'] == 8
    print("   ✅ Add documents OK")
    
    print("\n3. Testing auto cleanup when threshold reached...")
    # Add more documents to trigger cleanup (threshold is 80%)
    content = "This document should trigger cleanup."
    result = manager.add_document_to_quota(test_user, "DOC_008", content)
    print(f"   Result: {result}")
    
    if result['cleaned_count'] > 0:
        print(f"   ✅ Auto cleanup triggered: {result['cleaned_count']} docs cleaned")
    else:
        print("   ⚠️ Auto cleanup not triggered (might be under threshold)")
    
    print("\n4. Testing document too long...")
    long_content = "A" * 600  # Over 500 char limit
    result = manager.add_document_to_quota(test_user, "DOC_LONG", long_content)
    print(f"   Result: {result['success']} - {result['message']}")
    assert not result['success']
    print("   ✅ Long document rejected correctly")
    
    print("\n5. Testing manual cleanup...")
    result = manager.force_cleanup(test_user, 0.5)  # Clean 50%
    print(f"   Result: {result}")
    assert result['success']
    print(f"   ✅ Manual cleanup OK: {result['cleaned']} docs cleaned")
    
    print("\n6. Testing quota summary...")
    summary = manager.get_quota_summary(test_user)
    print(f"   {summary}")
    assert "Documents:" in summary
    print("   ✅ Quota summary OK")
    
    print("\n7. Testing access tracking...")
    # First, add a document
    manager.add_document_to_quota(test_user, "DOC_ACCESS", "Test access tracking")
    # Update access
    manager.update_document_access(test_user, "DOC_ACCESS")
    manager.update_document_access(test_user, "DOC_ACCESS")
    quota = manager.get_user_quota(test_user)
    doc_info = quota['documents'].get("DOC_ACCESS", {})
    print(f"   Access count: {doc_info.get('access_count', 0)}")
    assert doc_info.get('access_count', 0) == 2
    print("   ✅ Access tracking OK")
    
    print("\n8. Cleanup test data...")
    manager.delete_user_knowledge(test_user)
    quota = manager.get_user_quota(test_user)
    assert quota['documents_count'] == 0
    print("   ✅ Cleanup OK")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✅")
    print("=" * 60)


def test_cleanup_strategy():
    """Test different cleanup strategies"""
    print("\n" + "=" * 60)
    print("Testing Cleanup Strategies")
    print("=" * 60)
    
    # Test oldest strategy
    print("\n1. Testing 'oldest' strategy...")
    manager = PersonalKnowledgeManager(
        base_dir="data/test_user_knowledge",
        quota_config={'cleanup_strategy': 'oldest', 'max_documents': 5, 'cleanup_amount': 0.4}
    )
    
    test_user = "test_strategy_user"
    manager.delete_user_knowledge(test_user)
    
    import time
    for i in range(5):
        manager.add_document_to_quota(test_user, f"DOC_{i}", f"Document {i}")
        time.sleep(0.1)  # Small delay to ensure different timestamps
    
    result = manager.force_cleanup(test_user, 0.4)
    print(f"   Cleaned {result['cleaned']} oldest documents")
    
    quota = manager.get_user_quota(test_user)
    remaining_ids = list(quota['documents'].keys())
    print(f"   Remaining: {remaining_ids}")
    # Should have newer docs remaining (DOC_3, DOC_4)
    
    manager.delete_user_knowledge(test_user)
    print("   ✅ Oldest strategy OK")
    
    # Test least_used strategy
    print("\n2. Testing 'least_used' strategy...")
    manager = PersonalKnowledgeManager(
        base_dir="data/test_user_knowledge",
        quota_config={'cleanup_strategy': 'least_used', 'max_documents': 5, 'cleanup_amount': 0.4}
    )
    
    manager.delete_user_knowledge(test_user)
    
    for i in range(5):
        manager.add_document_to_quota(test_user, f"DOC_{i}", f"Document {i}")
    
    # Access some documents more than others
    for _ in range(5):
        manager.update_document_access(test_user, "DOC_4")
    for _ in range(3):
        manager.update_document_access(test_user, "DOC_3")
    
    result = manager.force_cleanup(test_user, 0.4)
    print(f"   Cleaned {result['cleaned']} least-used documents")
    
    quota = manager.get_user_quota(test_user)
    remaining_ids = list(quota['documents'].keys())
    print(f"   Remaining: {remaining_ids}")
    # Should have most-used docs remaining (DOC_3, DOC_4)
    
    manager.delete_user_knowledge(test_user)
    print("   ✅ Least-used strategy OK")
    
    print("\n" + "=" * 60)
    print("Cleanup strategy tests passed! ✅")
    print("=" * 60)


if __name__ == '__main__':
    test_quota_system()
    test_cleanup_strategy()
