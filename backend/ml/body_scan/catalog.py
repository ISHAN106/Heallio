"""Per-class metadata for the DermNet-trained body/skin scan model.

Each entry maps a DermNet class slug (see prepare_dataset.py's _slugify) to a
patient-facing label plus non-diagnostic guidance. Urgency levels: "low",
"review" (worth a routine check), "moderate", "urgent" (see a clinician soon).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkinConditionProfile:
    display_name: str
    urgency_level: str
    summary: str
    recommendation: str


_DEFAULT = SkinConditionProfile(
    display_name="Unclassified skin finding",
    urgency_level="review",
    summary="The image pattern didn't map clearly to a known category.",
    recommendation="Consider a clearer, well-lit photo, or have it looked at by a clinician for a proper assessment.",
)

SKIN_CONDITION_PROFILES: dict[str, SkinConditionProfile] = {
    "acne_and_rosacea_photos": SkinConditionProfile(
        display_name="Acne or rosacea pattern",
        urgency_level="low",
        summary="The image pattern resembles common acne or rosacea.",
        recommendation="Gentle cleansing, avoiding pore-clogging products, and consistency usually help. See a "
        "dermatologist if it's painful, spreading fast, or not improving after a few weeks of routine care.",
    ),
    "actinic_keratosis_basal_cell_carcinoma_and_other_malignant_lesions": SkinConditionProfile(
        display_name="Possible precancerous or malignant lesion",
        urgency_level="urgent",
        summary="The image pattern shares features with lesions that can sometimes be precancerous or cancerous.",
        recommendation="This category needs an in-person dermatologist evaluation, ideally soon -- this tool cannot "
        "rule out or confirm cancer from a photo alone.",
    ),
    "atopic_dermatitis_photos": SkinConditionProfile(
        display_name="Atopic dermatitis (eczema-type) pattern",
        urgency_level="review",
        summary="The image pattern resembles atopic dermatitis, a common chronic eczema.",
        recommendation="Moisturize regularly and avoid known triggers. See a clinician if it's intensely itchy, "
        "cracked, oozing, or not responding to basic skin care.",
    ),
    "bullous_disease_photos": SkinConditionProfile(
        display_name="Blistering (bullous) skin pattern",
        urgency_level="moderate",
        summary="The image pattern resembles a blistering skin condition.",
        recommendation="Blistering conditions can have several causes and sometimes need prescription treatment -- "
        "have this evaluated by a clinician, sooner if blisters are spreading or you feel unwell.",
    ),
    "cellulitis_impetigo_and_other_bacterial_infections": SkinConditionProfile(
        display_name="Possible bacterial skin infection",
        urgency_level="urgent",
        summary="The image pattern resembles a bacterial skin infection such as cellulitis or impetigo.",
        recommendation="These can worsen quickly and may need antibiotics. Seek medical care promptly, especially "
        "with spreading redness, warmth, swelling, fever, or pain.",
    ),
    "eczema_photos": SkinConditionProfile(
        display_name="Eczema pattern",
        urgency_level="review",
        summary="The image pattern resembles eczema (dermatitis).",
        recommendation="Moisturize, avoid irritants and known triggers, and use lukewarm (not hot) water when "
        "washing. Consult a clinician if it flares badly, gets infected-looking, or doesn't settle.",
    ),
    "exanthems_and_drug_eruptions": SkinConditionProfile(
        display_name="Widespread rash / possible drug eruption",
        urgency_level="moderate",
        summary="The image pattern resembles a widespread rash, sometimes linked to infections or medication reactions.",
        recommendation="If this started after a new medication, or comes with fever, facial swelling, or trouble "
        "breathing, seek urgent medical care. Otherwise, have a clinician assess it soon.",
    ),
    "hair_loss_photos_alopecia_and_other_hair_diseases": SkinConditionProfile(
        display_name="Hair loss / alopecia pattern",
        urgency_level="low",
        summary="The image pattern resembles a hair loss or scalp condition.",
        recommendation="Hair loss has many causes (stress, hormones, autoimmune, genetics). A dermatologist can "
        "help identify the cause and options if it's bothering you or progressing.",
    ),
    "herpes_hpv_and_other_stds_photos": SkinConditionProfile(
        display_name="Possible viral / sexually transmitted skin condition",
        urgency_level="moderate",
        summary="The image pattern resembles a viral skin condition sometimes associated with STIs.",
        recommendation="These are best confirmed and treated by a clinician, both for your care and to discuss "
        "any needed precautions or partner notification. Please seek an in-person or telehealth evaluation.",
    ),
    "light_diseases_and_disorders_of_pigmentation": SkinConditionProfile(
        display_name="Pigmentation change pattern",
        urgency_level="low",
        summary="The image pattern resembles a pigmentation disorder (patchy lighter or darker skin).",
        recommendation="Usually not urgent, but a dermatologist can confirm the cause and discuss options if it's "
        "spreading or affecting you cosmetically.",
    ),
    "lupus_and_other_connective_tissue_diseases": SkinConditionProfile(
        display_name="Possible connective tissue disease pattern",
        urgency_level="moderate",
        summary="The image pattern shares features seen in lupus and related connective tissue diseases.",
        recommendation="These conditions can affect more than skin. Please discuss this with a doctor, especially "
        "if you also have joint pain, fatigue, or sun sensitivity.",
    ),
    "melanoma_skin_cancer_nevi_and_moles": SkinConditionProfile(
        display_name="Mole/lesion needing cancer screening",
        urgency_level="urgent",
        summary="The image pattern falls in a category that includes melanoma as well as ordinary moles.",
        recommendation="Any new, changing, asymmetric, or irregularly bordered/colored mole should be checked by "
        "a dermatologist promptly -- this tool cannot distinguish benign moles from melanoma reliably.",
    ),
    "nail_fungus_and_other_nail_disease": SkinConditionProfile(
        display_name="Nail fungus / nail disease pattern",
        urgency_level="low",
        summary="The image pattern resembles a fungal or other nail condition.",
        recommendation="Usually not urgent. Keep the area clean and dry; see a clinician for persistent or "
        "worsening nail changes, especially with pain or spreading discoloration.",
    ),
    "poison_ivy_photos_and_other_contact_dermatitis": SkinConditionProfile(
        display_name="Contact dermatitis pattern",
        urgency_level="review",
        summary="The image pattern resembles an allergic or irritant contact dermatitis (e.g. poison ivy).",
        recommendation="Wash the area, avoid the suspected irritant, and use a cool compress for comfort. Seek "
        "care if it's spreading rapidly, on the face, or affecting breathing.",
    ),
    "psoriasis_pictures_lichen_planus_and_related_diseases": SkinConditionProfile(
        display_name="Psoriasis / lichen planus pattern",
        urgency_level="review",
        summary="The image pattern resembles psoriasis or a related chronic skin condition.",
        recommendation="These are chronic but manageable conditions. A dermatologist can confirm the diagnosis and "
        "discuss treatment options if it's uncomfortable or spreading.",
    ),
    "scabies_lyme_disease_and_other_infestations_and_bites": SkinConditionProfile(
        display_name="Possible infestation or bite-related pattern",
        urgency_level="moderate",
        summary="The image pattern resembles scabies, insect bites, or a tick-related condition.",
        recommendation="Have this assessed by a clinician, particularly if you recall a tick bite, notice a "
        "spreading rash or bullseye pattern, or have fever -- some causes need prompt treatment.",
    ),
    "seborrheic_keratoses_and_other_benign_tumors": SkinConditionProfile(
        display_name="Likely benign skin growth",
        urgency_level="low",
        summary="The image pattern resembles a typically benign skin growth such as seborrheic keratosis.",
        recommendation="Usually harmless, but have a clinician confirm, especially if the growth changes shape, "
        "color, or size, or becomes irritated.",
    ),
    "systemic_disease": SkinConditionProfile(
        display_name="Skin sign of possible systemic disease",
        urgency_level="moderate",
        summary="The image pattern resembles skin changes sometimes associated with an internal/systemic condition.",
        recommendation="Skin changes like this are worth discussing with a doctor alongside your broader symptoms, "
        "since the underlying cause may need a full evaluation.",
    ),
    "tinea_ringworm_candidiasis_and_other_fungal_infections": SkinConditionProfile(
        display_name="Fungal skin infection pattern",
        urgency_level="review",
        summary="The image pattern resembles a fungal skin infection (ringworm, candidiasis, etc.).",
        recommendation="Keep the area clean and dry; over-the-counter antifungals often help. See a clinician if "
        "it spreads, doesn't improve, or recurs.",
    ),
    "urticaria_hives": SkinConditionProfile(
        display_name="Hives (urticaria) pattern",
        urgency_level="review",
        summary="The image pattern resembles hives, usually from an allergic or irritant reaction.",
        recommendation="Antihistamines often help mild cases. Seek urgent care if it comes with facial/lip/throat "
        "swelling, trouble breathing, or dizziness -- these can signal a severe allergic reaction.",
    ),
    "vascular_tumors": SkinConditionProfile(
        display_name="Vascular growth pattern",
        urgency_level="review",
        summary="The image pattern resembles a vascular skin growth (e.g. hemangioma).",
        recommendation="Most vascular growths are benign, but have a clinician confirm, especially if it's growing "
        "quickly, bleeding, or new in an adult.",
    ),
    "vasculitis_photos": SkinConditionProfile(
        display_name="Possible vasculitis pattern",
        urgency_level="moderate",
        summary="The image pattern resembles vasculitis, an inflammation of blood vessels that can affect the skin.",
        recommendation="This can sometimes indicate a broader inflammatory condition -- please have it evaluated "
        "by a doctor, sooner if you also have fever, joint pain, or feel unwell.",
    ),
    "warts_molluscum_and_other_viral_infections": SkinConditionProfile(
        display_name="Wart / viral skin growth pattern",
        urgency_level="low",
        summary="The image pattern resembles a common viral skin growth such as warts or molluscum contagiosum.",
        recommendation="Usually harmless and often resolves on its own or with over-the-counter treatment. See a "
        "clinician if it spreads a lot, is painful, or doesn't resolve over a few months.",
    ),
}


def profile_for_label(label: str) -> SkinConditionProfile:
    return SKIN_CONDITION_PROFILES.get(label, _DEFAULT)
