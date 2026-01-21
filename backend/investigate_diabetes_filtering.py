"""
Investigate diabetes filtering - why so many foods are marked unsafe.
Check overlap between diabetic_safe flags and condition compatibility.
"""
from app.database import SessionLocal
from app.platform.data.models.kb_food_master import KBFoodMaster
from app.platform.data.models.kb_food_exchange_profile import KBFoodExchangeProfile
from app.platform.data.models.kb_food_mnt_profile import KBFoodMNTProfile
from app.platform.data.models.kb_food_condition_compatibility import KBFoodConditionCompatibility

db = SessionLocal()

print("=" * 80)
print("INVESTIGATING DIABETES FILTERING")
print("=" * 80)

# Get all cereal foods
cereal_foods = db.query(KBFoodMaster).join(
    KBFoodExchangeProfile
).outerjoin(
    KBFoodMNTProfile
).filter(
    KBFoodMaster.status == 'active',
    KBFoodExchangeProfile.exchange_category == 'cereal'
).limit(30).all()

print(f"\nAnalyzing {len(cereal_foods)} cereal foods:")
print("-" * 80)

diabetic_false_count = 0
diabetic_true_count = 0
diabetic_none_count = 0

compat_safe_count = 0
compat_contraindicated_count = 0
compat_no_record_count = 0
compat_avoid_count = 0

overlap_issues = []

for food in cereal_foods:
    # Get diabetic_safe from medical_tags
    medical_tags = {}
    diabetic_safe = None
    if food.mnt_profile and food.mnt_profile.medical_tags:
        medical_tags = food.mnt_profile.medical_tags
        diabetic_safe = medical_tags.get('diabetic_safe')
    
    # Get condition compatibility
    compat = db.query(KBFoodConditionCompatibility).filter(
        KBFoodConditionCompatibility.food_id == food.food_id,
        KBFoodConditionCompatibility.condition_id == 'diabetes',
        KBFoodConditionCompatibility.status == 'active'
    ).first()
    
    compat_level = compat.compatibility if compat else None
    
    # Count diabetic_safe
    if diabetic_safe is False:
        diabetic_false_count += 1
    elif diabetic_safe is True:
        diabetic_true_count += 1
    else:
        diabetic_none_count += 1
    
    # Count compatibility
    if compat_level:
        if compat_level.lower() == 'safe':
            compat_safe_count += 1
        elif compat_level.lower() == 'contraindicated':
            compat_contraindicated_count += 1
        elif compat_level.lower() == 'avoid':
            compat_avoid_count += 1
    else:
        compat_no_record_count += 1
    
    # Check for conflicts/overlap
    if diabetic_safe is False and compat_level and compat_level.lower() == 'safe':
        overlap_issues.append({
            'food': food.display_name,
            'diabetic_safe': diabetic_safe,
            'compatibility': compat_level
        })
    elif diabetic_safe is True and compat_level and compat_level.lower() == 'contraindicated':
        overlap_issues.append({
            'food': food.display_name,
            'diabetic_safe': diabetic_safe,
            'compatibility': compat_level
        })
    
    # Show first 5 examples
    if len([f for f in cereal_foods[:5] if f.food_id == food.food_id]) > 0:
        print(f"\n{food.display_name}:")
        print(f"  diabetic_safe: {diabetic_safe}")
        print(f"  condition_compatibility: {compat_level or 'no_record'}")
        if medical_tags.get('glycemic_classification'):
            print(f"  glycemic_classification: {medical_tags.get('glycemic_classification')}")

print("\n" + "=" * 80)
print("SUMMARY STATISTICS")
print("=" * 80)
print(f"\ndiabetic_safe flags:")
print(f"  False (unsafe): {diabetic_false_count}")
print(f"  True (safe): {diabetic_true_count}")
print(f"  None (unknown): {diabetic_none_count}")

print(f"\ncondition_compatibility (for 'diabetes'):")
print(f"  safe: {compat_safe_count}")
print(f"  contraindicated: {compat_contraindicated_count}")
print(f"  avoid: {compat_avoid_count}")
print(f"  no_record: {compat_no_record_count}")

if overlap_issues:
    print(f"\n⚠️  CONFLICTS FOUND ({len(overlap_issues)}):")
    print("Foods where diabetic_safe and condition_compatibility disagree:")
    for issue in overlap_issues[:5]:
        print(f"  - {issue['food']}: diabetic_safe={issue['diabetic_safe']}, compatibility={issue['compatibility']}")
else:
    print("\nOK: No conflicts found between diabetic_safe and condition_compatibility")

print("\n" + "=" * 80)
print("ANALYSIS:")
print("=" * 80)
print("""
The diabetic_safe flag is set based on:
1. Food exclusion tags matching MNT rules
2. Constraint compliance (macro/micro limits)

The condition_compatibility is set based on:
1. Medical tags (diabetic_safe flag)
2. Contraindications
3. Preferred conditions

QUESTION: Why do we need BOTH checks?
- If condition_compatibility already uses diabetic_safe, why check diabetic_safe separately?
- This creates duplication and potential conflicts.
""")

db.close()

