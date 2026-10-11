"""
Test suite for the safety layer — run without any API keys.

Usage:
    python tests/test_safety.py
"""

import sys
import io

# Fix Windows console encoding for emoji/Unicode output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.safety import detect_emergency, audit_response


def test_emergency_detection():
    """Test that emergency keywords trigger the safety short-circuit."""
    emergencies = [
        # English
        ("I have chest pain", True, "chest pain"),
        ("I can't breathe", True, "breathing difficulty"),
        ("sudden numbness on one side", True, "possible stroke"),
        ("heavy bleeding won't stop", True, "severe bleeding"),
        ("I passed out earlier", True, "unconsciousness"),
        ("I want to kill myself", True, "mental health crisis"),
        ("my throat is swelling", True, "severe allergic reaction"),
        ("my child is having a seizure", True, "seizure"),
        ("I think I overdosed", True, "poisoning / overdose"),
        # Hindi
        ("मुझे सीने में दर्द है", True, "chest pain (Hindi)"),
        ("सांस लेने में तकलीफ", True, "breathing difficulty (Hindi)"),
        ("बेहोश हो गया", True, "unconsciousness (Hindi)"),
        ("आत्महत्या करना चाहता हूँ", True, "mental health crisis (Hindi)"),
        # Non-emergencies
        ("I have a headache", False, None),
        ("my stomach hurts a little", False, None),
        ("what should I eat for cold", False, None),
        ("I feel tired", False, None),
    ]

    passed = 0
    failed = 0

    for text, expected_emergency, expected_label in emergencies:
        is_emerg, label, response = detect_emergency(text)

        if is_emerg != expected_emergency:
            print(f"  ❌ FAIL: '{text}'")
            print(f"     Expected emergency={expected_emergency}, got {is_emerg}")
            failed += 1
        elif expected_emergency and expected_label and expected_label not in (label or ""):
            print(f"  ❌ FAIL: '{text}'")
            print(f"     Expected label containing '{expected_label}', got '{label}'")
            failed += 1
        else:
            print(f"  ✅ PASS: '{text}' → emergency={is_emerg}, label={label}")
            passed += 1

    return passed, failed


def test_response_audit():
    """Test that post-LLM audit catches leaked dosages and diagnoses."""
    tests = [
        # Should flag dosage
        ("Take 500 mg of paracetamol", True, "dosage"),
        ("Give 2.5 ml to the child", True, "dosage"),
        ("One 10 mg tablet twice a day", True, "dosage"),
        # Should flag diagnosis
        ("You have diabetes", True, "diagnosis"),
        ("You are suffering from hypertension", True, "diagnosis"),
        # Clean responses (no flags)
        ("Please consult a doctor for the correct dosage.", False, ""),
        ("These symptoms are sometimes associated with dehydration.", False, ""),
        ("I recommend seeing a healthcare professional.", False, ""),
    ]

    passed = 0
    failed = 0

    for text, should_flag, flag_type in tests:
        result = audit_response(text)
        has_warning = "⚠️" in result

        if has_warning != should_flag:
            print(f"  ❌ FAIL: '{text[:50]}...'")
            print(f"     Expected warning={should_flag}, got {has_warning}")
            failed += 1
        else:
            print(f"  ✅ PASS: '{text[:50]}...' → flagged={has_warning}")
            passed += 1

    return passed, failed


if __name__ == "__main__":
    print("\n🔬 Testing Emergency Detection")
    print("=" * 60)
    p1, f1 = test_emergency_detection()

    print(f"\n🔬 Testing Response Audit")
    print("=" * 60)
    p2, f2 = test_response_audit()

    total_passed = p1 + p2
    total_failed = f1 + f2
    print(f"\n{'=' * 60}")
    print(f"Results: {total_passed} passed, {total_failed} failed")

    if total_failed > 0:
        print("❌ Some tests failed!")
        sys.exit(1)
    else:
        print("✅ All tests passed!")
        sys.exit(0)
