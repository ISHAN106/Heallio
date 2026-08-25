from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FoodProfile:
    key: str
    display_name: str
    portion_label: str
    portion_grams: float
    nutrition_per_100g: dict[str, float]
    micronutrients_per_100g: dict[str, float]
    contents: list[str]
    feature_center: np.ndarray
    feature_noise: float
    portion_noise: float
    suggested_meal_type: str


# Generic 14-dim feature center used for profiles that only exist to carry accurate
# nutrition data for CNN-predicted labels; the RF synthetic-data fallback path pads/
# clips this to the full feature dimension, so it only matters when no real image
# dataset is present yet and training falls back to synthetic samples.
_DEFAULT_CENTER = np.array(
    [0.6, 0.55, 0.42, 0.22, 0.19, 0.17, 0.55, 0.28, 0.22, 0.42, 0.12, 0.15, 0.62, 0.63], dtype=np.float32
)

FOOD_PROFILES: list[FoodProfile] = [
    FoodProfile(
        key="salad_bowl",
        display_name="Mixed salad bowl",
        portion_label="1 large bowl",
        portion_grams=180,
        nutrition_per_100g={"calories": 95, "carbs": 9, "protein": 4, "fat": 5, "fiber": 3, "sugar": 4},
        micronutrients_per_100g={"Vitamin A": 18, "Vitamin C": 22, "Folate": 14, "Iron": 7, "Potassium": 12},
        contents=["lettuce", "cucumber", "tomato", "seeds", "light dressing"],
        feature_center=np.array([0.28, 0.62, 0.27, 0.18, 0.17, 0.19, 0.64, 0.24, 0.18, 0.34, -0.05, 0.26, 0.62, 0.62], dtype=np.float32),
        feature_noise=0.05,
        portion_noise=22,
        suggested_meal_type="lunch",
    ),
    FoodProfile(
        key="pizza_slice",
        display_name="Veg pizza slice",
        portion_label="2 medium slices",
        portion_grams=210,
        nutrition_per_100g={"calories": 265, "carbs": 29, "protein": 11, "fat": 10, "fiber": 2, "sugar": 4},
        micronutrients_per_100g={"Vitamin A": 9, "Vitamin C": 11, "Calcium": 16, "Iron": 8, "Potassium": 7},
        contents=["wheat crust", "cheese", "tomato sauce", "capsicum", "onion"],
        feature_center=np.array([0.74, 0.52, 0.38, 0.27, 0.22, 0.18, 0.57, 0.46, 0.35, 0.61, 0.29, 0.34, 0.72, 0.68], dtype=np.float32),
        feature_noise=0.06,
        portion_noise=24,
        suggested_meal_type="dinner",
    ),
    FoodProfile(
        key="burger",
        display_name="Chicken burger",
        portion_label="1 burger",
        portion_grams=230,
        nutrition_per_100g={"calories": 240, "carbs": 23, "protein": 13, "fat": 11, "fiber": 2, "sugar": 4},
        micronutrients_per_100g={"Vitamin B3": 14, "Vitamin B12": 11, "Iron": 10, "Calcium": 6, "Potassium": 8},
        contents=["bun", "chicken patty", "lettuce", "tomato", "sauce"],
        feature_center=np.array([0.55, 0.42, 0.28, 0.31, 0.23, 0.18, 0.42, 0.39, 0.31, 0.54, 0.15, 0.17, 0.58, 0.62], dtype=np.float32),
        feature_noise=0.06,
        portion_noise=28,
        suggested_meal_type="lunch",
    ),
    FoodProfile(
        key="rice_bowl",
        display_name="Rice bowl",
        portion_label="1 medium bowl",
        portion_grams=250,
        nutrition_per_100g={"calories": 172, "carbs": 28, "protein": 4, "fat": 5, "fiber": 2, "sugar": 1},
        micronutrients_per_100g={"Vitamin B1": 6, "Vitamin B6": 5, "Magnesium": 8, "Iron": 5, "Potassium": 7},
        contents=["rice", "vegetables", "spices", "ghee"],
        feature_center=np.array([0.69, 0.63, 0.51, 0.15, 0.13, 0.11, 0.55, 0.12, 0.10, 0.29, 0.08, 0.11, 0.76, 0.7], dtype=np.float32),
        feature_noise=0.05,
        portion_noise=32,
        suggested_meal_type="lunch",
    ),
    FoodProfile(
        key="fruit_bowl",
        display_name="Mixed fruit bowl",
        portion_label="1 small bowl",
        portion_grams=160,
        nutrition_per_100g={"calories": 62, "carbs": 15, "protein": 1, "fat": 0, "fiber": 2, "sugar": 12},
        micronutrients_per_100g={"Vitamin C": 25, "Vitamin A": 10, "Folate": 7, "Potassium": 14, "Manganese": 9},
        contents=["apple", "banana", "berries", "melon"],
        feature_center=np.array([0.66, 0.48, 0.42, 0.26, 0.21, 0.23, 0.58, 0.41, 0.24, 0.48, 0.17, 0.19, 0.67, 0.63], dtype=np.float32),
        feature_noise=0.06,
        portion_noise=18,
        suggested_meal_type="snack",
    ),
    FoodProfile(
        key="creamy_pasta",
        display_name="Creamy pasta",
        portion_label="1 deep plate",
        portion_grams=240,
        nutrition_per_100g={"calories": 232, "carbs": 27, "protein": 7, "fat": 10, "fiber": 2, "sugar": 3},
        micronutrients_per_100g={"Vitamin B2": 7, "Vitamin B6": 6, "Calcium": 11, "Iron": 8, "Potassium": 7},
        contents=["pasta", "cream sauce", "herbs", "cheese"],
        feature_center=np.array([0.76, 0.65, 0.49, 0.26, 0.21, 0.2, 0.52, 0.24, 0.21, 0.56, 0.23, 0.24, 0.64, 0.64], dtype=np.float32),
        feature_noise=0.06,
        portion_noise=28,
        suggested_meal_type="dinner",
    ),
    FoodProfile(
        key="omelette",
        display_name="Egg omelette",
        portion_label="2 eggs with toppings",
        portion_grams=150,
        nutrition_per_100g={"calories": 154, "carbs": 2, "protein": 11, "fat": 11, "fiber": 0, "sugar": 1},
        micronutrients_per_100g={"Vitamin B12": 23, "Vitamin D": 12, "Iron": 6, "Choline": 18, "Selenium": 20},
        contents=["eggs", "onion", "tomato", "peppers", "oil"],
        feature_center=np.array([0.78, 0.70, 0.45, 0.18, 0.16, 0.14, 0.71, 0.26, 0.18, 0.39, 0.28, 0.12, 0.55, 0.6], dtype=np.float32),
        feature_noise=0.05,
        portion_noise=15,
        suggested_meal_type="breakfast",
    ),
    FoodProfile(
        key="soup",
        display_name="Soup bowl",
        portion_label="1 bowl",
        portion_grams=220,
        nutrition_per_100g={"calories": 78, "carbs": 10, "protein": 3, "fat": 3, "fiber": 2, "sugar": 3},
        micronutrients_per_100g={"Vitamin A": 8, "Vitamin C": 10, "Calcium": 5, "Iron": 4, "Potassium": 9},
        contents=["broth", "vegetables", "herbs", "seasoning"],
        feature_center=np.array([0.52, 0.42, 0.34, 0.19, 0.16, 0.14, 0.44, 0.19, 0.17, 0.31, 0.11, 0.09, 0.59, 0.64], dtype=np.float32),
        feature_noise=0.05,
        portion_noise=20,
        suggested_meal_type="dinner",
    ),
    FoodProfile(
        key="sandwich",
        display_name="Veg sandwich",
        portion_label="1 sandwich",
        portion_grams=180,
        nutrition_per_100g={"calories": 185, "carbs": 21, "protein": 7, "fat": 7, "fiber": 3, "sugar": 3},
        micronutrients_per_100g={"Vitamin B1": 7, "Vitamin C": 8, "Folate": 6, "Iron": 6, "Potassium": 7},
        contents=["bread", "vegetables", "spread", "cheese"],
        feature_center=np.array([0.67, 0.56, 0.41, 0.21, 0.18, 0.16, 0.51, 0.21, 0.18, 0.45, 0.14, 0.14, 0.6, 0.62], dtype=np.float32),
        feature_noise=0.05,
        portion_noise=20,
        suggested_meal_type="snack",
    ),
    # -- Indian dishes --
    FoodProfile(
        key="butter_chicken",
        display_name="Butter chicken",
        portion_label="1 bowl with gravy",
        portion_grams=250,
        nutrition_per_100g={"calories": 190, "carbs": 6, "protein": 14, "fat": 12, "fiber": 1, "sugar": 3},
        micronutrients_per_100g={"Vitamin B12": 14, "Iron": 8, "Calcium": 6, "Potassium": 9},
        contents=["chicken", "tomato gravy", "butter", "cream", "spices"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.08,
        portion_noise=30,
        suggested_meal_type="dinner",
    ),
    FoodProfile(
        key="paneer_tikka",
        display_name="Paneer tikka",
        portion_label="1 plate (6-8 pieces)",
        portion_grams=180,
        nutrition_per_100g={"calories": 210, "carbs": 6, "protein": 14, "fat": 15, "fiber": 1, "sugar": 2},
        micronutrients_per_100g={"Calcium": 22, "Vitamin A": 10, "Iron": 6, "Potassium": 6},
        contents=["paneer", "bell pepper", "onion", "yogurt marinade", "spices"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.08,
        portion_noise=24,
        suggested_meal_type="snack",
    ),
    FoodProfile(
        key="palak_paneer",
        display_name="Palak paneer",
        portion_label="1 bowl with gravy",
        portion_grams=230,
        nutrition_per_100g={"calories": 150, "carbs": 7, "protein": 9, "fat": 10, "fiber": 3, "sugar": 2},
        micronutrients_per_100g={"Vitamin A": 40, "Vitamin C": 18, "Iron": 15, "Calcium": 20},
        contents=["spinach", "paneer", "cream", "spices"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.08,
        portion_noise=26,
        suggested_meal_type="dinner",
    ),
    FoodProfile(
        key="chana_masala",
        display_name="Chana masala",
        portion_label="1 bowl",
        portion_grams=220,
        nutrition_per_100g={"calories": 140, "carbs": 20, "protein": 7, "fat": 4, "fiber": 6, "sugar": 3},
        micronutrients_per_100g={"Iron": 14, "Folate": 20, "Potassium": 10, "Magnesium": 9},
        contents=["chickpeas", "onion-tomato gravy", "spices"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.07,
        portion_noise=26,
        suggested_meal_type="lunch",
    ),
    FoodProfile(
        key="dal_tadka",
        display_name="Dal tadka",
        portion_label="1 bowl",
        portion_grams=200,
        nutrition_per_100g={"calories": 105, "carbs": 15, "protein": 6, "fat": 3, "fiber": 4, "sugar": 1},
        micronutrients_per_100g={"Iron": 10, "Folate": 18, "Potassium": 8, "Magnesium": 8},
        contents=["lentils", "tempered spices", "ghee", "onion", "tomato"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.06,
        portion_noise=24,
        suggested_meal_type="lunch",
    ),
    FoodProfile(
        key="aloo_gobi",
        display_name="Aloo gobi",
        portion_label="1 bowl",
        portion_grams=200,
        nutrition_per_100g={"calories": 120, "carbs": 16, "protein": 3, "fat": 5, "fiber": 4, "sugar": 3},
        micronutrients_per_100g={"Vitamin C": 30, "Potassium": 10, "Folate": 10, "Iron": 6},
        contents=["potato", "cauliflower", "spices"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.07,
        portion_noise=24,
        suggested_meal_type="lunch",
    ),
    FoodProfile(
        key="biryani",
        display_name="Chicken biryani",
        portion_label="1 plate",
        portion_grams=280,
        nutrition_per_100g={"calories": 195, "carbs": 24, "protein": 9, "fat": 7, "fiber": 1, "sugar": 1},
        micronutrients_per_100g={"Iron": 8, "Vitamin B6": 6, "Potassium": 7, "Magnesium": 6},
        contents=["basmati rice", "chicken or vegetables", "spices", "fried onions"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.07,
        portion_noise=32,
        suggested_meal_type="lunch",
    ),
    FoodProfile(
        key="samosa",
        display_name="Samosa",
        portion_label="2 pieces",
        portion_grams=100,
        nutrition_per_100g={"calories": 300, "carbs": 32, "protein": 5, "fat": 17, "fiber": 3, "sugar": 2},
        micronutrients_per_100g={"Iron": 7, "Potassium": 6, "Vitamin C": 5},
        contents=["potato filling", "peas", "spices", "fried pastry"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.07,
        portion_noise=18,
        suggested_meal_type="snack",
    ),
    FoodProfile(
        key="idli",
        display_name="Idli with chutney",
        portion_label="3 idlis",
        portion_grams=180,
        nutrition_per_100g={"calories": 130, "carbs": 26, "protein": 4, "fat": 1, "fiber": 1, "sugar": 1},
        micronutrients_per_100g={"Iron": 5, "Calcium": 4, "Potassium": 5},
        contents=["fermented rice-lentil batter", "coconut chutney"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.06,
        portion_noise=20,
        suggested_meal_type="breakfast",
    ),
    FoodProfile(
        key="dosa",
        display_name="Masala dosa",
        portion_label="1 dosa",
        portion_grams=200,
        nutrition_per_100g={"calories": 168, "carbs": 26, "protein": 4, "fat": 5, "fiber": 2, "sugar": 1},
        micronutrients_per_100g={"Iron": 6, "Potassium": 8, "Vitamin C": 6},
        contents=["fermented rice-lentil crepe", "spiced potato filling"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.06,
        portion_noise=24,
        suggested_meal_type="breakfast",
    ),
    FoodProfile(
        key="chapati",
        display_name="Chapati / roti",
        portion_label="2 pieces",
        portion_grams=100,
        nutrition_per_100g={"calories": 250, "carbs": 47, "protein": 8, "fat": 4, "fiber": 6, "sugar": 1},
        micronutrients_per_100g={"Iron": 10, "Magnesium": 12, "Potassium": 6},
        contents=["whole wheat flour", "water", "ghee"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.06,
        portion_noise=14,
        suggested_meal_type="dinner",
    ),
    FoodProfile(
        key="naan",
        display_name="Butter naan",
        portion_label="1 piece",
        portion_grams=90,
        nutrition_per_100g={"calories": 310, "carbs": 50, "protein": 9, "fat": 8, "fiber": 2, "sugar": 3},
        micronutrients_per_100g={"Calcium": 8, "Iron": 8, "Potassium": 5},
        contents=["refined flour", "yogurt", "butter"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.06,
        portion_noise=14,
        suggested_meal_type="dinner",
    ),
    FoodProfile(
        key="poha",
        display_name="Poha",
        portion_label="1 plate",
        portion_grams=180,
        nutrition_per_100g={"calories": 130, "carbs": 24, "protein": 3, "fat": 3, "fiber": 2, "sugar": 3},
        micronutrients_per_100g={"Iron": 12, "Folate": 8, "Potassium": 7},
        contents=["flattened rice", "onion", "peanuts", "curry leaves", "turmeric"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.06,
        portion_noise=20,
        suggested_meal_type="breakfast",
    ),
    FoodProfile(
        key="upma",
        display_name="Upma",
        portion_label="1 bowl",
        portion_grams=180,
        nutrition_per_100g={"calories": 135, "carbs": 22, "protein": 4, "fat": 4, "fiber": 2, "sugar": 1},
        micronutrients_per_100g={"Iron": 6, "Magnesium": 6, "Potassium": 6},
        contents=["semolina", "vegetables", "mustard seed tempering"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.06,
        portion_noise=20,
        suggested_meal_type="breakfast",
    ),
    FoodProfile(
        key="tandoori_chicken",
        display_name="Tandoori chicken",
        portion_label="2 pieces",
        portion_grams=220,
        nutrition_per_100g={"calories": 165, "carbs": 3, "protein": 24, "fat": 6, "fiber": 0, "sugar": 1},
        micronutrients_per_100g={"Vitamin B12": 18, "Iron": 8, "Potassium": 10},
        contents=["chicken", "yogurt marinade", "tandoori spices"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.07,
        portion_noise=26,
        suggested_meal_type="dinner",
    ),
    FoodProfile(
        key="gulab_jamun",
        display_name="Gulab jamun",
        portion_label="2 pieces",
        portion_grams=80,
        nutrition_per_100g={"calories": 340, "carbs": 52, "protein": 5, "fat": 13, "fiber": 0, "sugar": 45},
        micronutrients_per_100g={"Calcium": 8, "Iron": 3},
        contents=["milk solids", "sugar syrup", "cardamom"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.06,
        portion_noise=12,
        suggested_meal_type="snack",
    ),
    # -- Western dishes --
    FoodProfile(
        key="grilled_chicken",
        display_name="Grilled chicken breast",
        portion_label="1 breast with sides",
        portion_grams=220,
        nutrition_per_100g={"calories": 165, "carbs": 2, "protein": 28, "fat": 5, "fiber": 1, "sugar": 1},
        micronutrients_per_100g={"Vitamin B6": 18, "Vitamin B12": 8, "Potassium": 9, "Iron": 5},
        contents=["chicken breast", "herbs", "olive oil", "vegetables"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.07,
        portion_noise=26,
        suggested_meal_type="dinner",
    ),
    FoodProfile(
        key="steak",
        display_name="Grilled steak",
        portion_label="1 steak with sides",
        portion_grams=250,
        nutrition_per_100g={"calories": 250, "carbs": 0, "protein": 26, "fat": 16, "fiber": 0, "sugar": 0},
        micronutrients_per_100g={"Iron": 15, "Vitamin B12": 30, "Zinc": 25, "Potassium": 8},
        contents=["beef steak", "butter", "herbs"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.07,
        portion_noise=30,
        suggested_meal_type="dinner",
    ),
    FoodProfile(
        key="pasta_bolognese",
        display_name="Spaghetti bolognese",
        portion_label="1 deep plate",
        portion_grams=260,
        nutrition_per_100g={"calories": 158, "carbs": 18, "protein": 8, "fat": 6, "fiber": 2, "sugar": 4},
        micronutrients_per_100g={"Iron": 10, "Vitamin C": 8, "Calcium": 6, "Potassium": 8},
        contents=["spaghetti", "minced beef", "tomato sauce", "herbs"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.07,
        portion_noise=30,
        suggested_meal_type="dinner",
    ),
    FoodProfile(
        key="tacos",
        display_name="Tacos",
        portion_label="2 tacos",
        portion_grams=200,
        nutrition_per_100g={"calories": 210, "carbs": 20, "protein": 10, "fat": 10, "fiber": 3, "sugar": 2},
        micronutrients_per_100g={"Vitamin A": 12, "Vitamin C": 14, "Iron": 8, "Calcium": 10},
        contents=["tortilla", "meat or beans", "cheese", "salsa", "lettuce"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.07,
        portion_noise=24,
        suggested_meal_type="lunch",
    ),
    FoodProfile(
        key="sushi",
        display_name="Sushi platter",
        portion_label="8 pieces",
        portion_grams=200,
        nutrition_per_100g={"calories": 145, "carbs": 25, "protein": 6, "fat": 2, "fiber": 1, "sugar": 3},
        micronutrients_per_100g={"Vitamin B12": 10, "Iodine": 15, "Potassium": 5},
        contents=["sushi rice", "fish or vegetables", "nori", "soy sauce"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.06,
        portion_noise=20,
        suggested_meal_type="dinner",
    ),
    FoodProfile(
        key="pancakes",
        display_name="Pancakes",
        portion_label="3 pancakes with syrup",
        portion_grams=180,
        nutrition_per_100g={"calories": 260, "carbs": 40, "protein": 6, "fat": 8, "fiber": 1, "sugar": 16},
        micronutrients_per_100g={"Calcium": 10, "Iron": 8, "Vitamin B2": 8},
        contents=["flour", "eggs", "milk", "butter", "maple syrup"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.06,
        portion_noise=20,
        suggested_meal_type="breakfast",
    ),
    FoodProfile(
        key="french_fries",
        display_name="French fries",
        portion_label="1 regular serving",
        portion_grams=140,
        nutrition_per_100g={"calories": 315, "carbs": 41, "protein": 4, "fat": 15, "fiber": 4, "sugar": 1},
        micronutrients_per_100g={"Vitamin C": 15, "Potassium": 12, "Iron": 5},
        contents=["potato", "oil", "salt"],
        feature_center=_DEFAULT_CENTER,
        feature_noise=0.06,
        portion_noise=16,
        suggested_meal_type="snack",
    ),
]

# -- Category nutrition templates for the bulk "Indian Food Images" Kaggle dataset (80 classes) --
_SWEET_FRIED_SYRUP = {"calories": 380, "carbs": 55, "protein": 4, "fat": 16, "fiber": 1, "sugar": 42}
_SWEET_MILK_SOLID = {"calories": 340, "carbs": 40, "protein": 7, "fat": 17, "fiber": 0, "sugar": 32}
_SWEET_MILK_PUDDING = {"calories": 200, "carbs": 26, "protein": 6, "fat": 8, "fiber": 0, "sugar": 20}
_SAVORY_CURRY_VEG = {"calories": 150, "carbs": 12, "protein": 5, "fat": 9, "fiber": 3, "sugar": 3}
_SAVORY_CURRY_MEAT = {"calories": 195, "carbs": 6, "protein": 17, "fat": 12, "fiber": 1, "sugar": 2}
_GRILLED_MEAT = {"calories": 180, "carbs": 3, "protein": 25, "fat": 7, "fiber": 0, "sugar": 1}
_SAVORY_FRIED_SNACK = {"calories": 320, "carbs": 34, "protein": 6, "fat": 18, "fiber": 2, "sugar": 2}
_BREAD_FRIED = {"calories": 320, "carbs": 45, "protein": 8, "fat": 12, "fiber": 2, "sugar": 2}
_SAVORY_STEAMED = {"calories": 150, "carbs": 24, "protein": 5, "fat": 4, "fiber": 2, "sugar": 1}
_THALI_MIXED = {"calories": 250, "carbs": 32, "protein": 8, "fat": 10, "fiber": 4, "sugar": 4}
_DRINK_DAIRY = {"calories": 90, "carbs": 12, "protein": 3, "fat": 3, "fiber": 0, "sugar": 10}
_BAKED_SNACK = {"calories": 290, "carbs": 40, "protein": 9, "fat": 10, "fiber": 5, "sugar": 2}

_MICRO_SWEET = {"Calcium": 8, "Iron": 4}
_MICRO_MEAT = {"Vitamin B12": 12, "Iron": 8, "Potassium": 8}
_MICRO_SAVORY = {"Iron": 8, "Vitamin A": 10, "Potassium": 8}
_MEAT_TEMPLATES = (_SAVORY_CURRY_MEAT, _GRILLED_MEAT)
_SWEET_TEMPLATES = (_SWEET_FRIED_SYRUP, _SWEET_MILK_SOLID, _SWEET_MILK_PUDDING, _DRINK_DAIRY)

# (key, display_name, nutrition_template, portion_grams, portion_label, meal_type, contents)
_INDIAN_DATASET_ENTRIES: list[tuple[str, str, dict, float, str, str, list[str]]] = [
    ("adhirasam", "Adhirasam", _SWEET_FRIED_SYRUP, 60, "2 pieces", "snack", ["rice flour", "jaggery", "ghee"]),
    ("aloo_matar", "Aloo matar", _SAVORY_CURRY_VEG, 200, "1 bowl", "lunch", ["potato", "green peas", "gravy"]),
    ("aloo_methi", "Aloo methi", _SAVORY_CURRY_VEG, 180, "1 bowl", "lunch", ["potato", "fenugreek leaves", "spices"]),
    ("aloo_shimla_mirch", "Aloo shimla mirch", _SAVORY_CURRY_VEG, 180, "1 bowl", "lunch", ["potato", "capsicum", "spices"]),
    ("aloo_tikki", "Aloo tikki", _SAVORY_FRIED_SNACK, 120, "2 pieces", "snack", ["mashed potato", "spices", "fried crust"]),
    ("anarsa", "Anarsa", _SWEET_FRIED_SYRUP, 60, "2 pieces", "snack", ["rice flour", "jaggery", "sesame"]),
    ("ariselu", "Ariselu", _SWEET_FRIED_SYRUP, 60, "2 pieces", "snack", ["rice flour", "jaggery"]),
    ("bandar_laddu", "Bandar laddu", _SWEET_MILK_SOLID, 50, "2 pieces", "snack", ["gram flour", "ghee", "sugar"]),
    ("basundi", "Basundi", _SWEET_MILK_PUDDING, 150, "1 bowl", "snack", ["thickened milk", "sugar", "nuts", "cardamom"]),
    ("bhatura", "Bhatura", _BREAD_FRIED, 90, "1 piece", "lunch", ["refined flour", "yogurt", "deep fried"]),
    ("bhindi_masala", "Bhindi masala", _SAVORY_CURRY_VEG, 180, "1 bowl", "lunch", ["okra", "onion-tomato masala"]),
    ("boondi", "Boondi", _SWEET_FRIED_SYRUP, 60, "1 small bowl", "snack", ["gram flour droplets", "sugar syrup"]),
    ("chak_hao_kheer", "Chak-hao kheer", _SWEET_MILK_PUDDING, 180, "1 bowl", "snack", ["black rice", "milk", "sugar"]),
    ("cham_cham", "Cham cham", _SWEET_MILK_SOLID, 80, "2 pieces", "snack", ["chhena", "sugar syrup", "coconut"]),
    ("chhena_kheeri", "Chhena kheeri", _SWEET_MILK_PUDDING, 150, "1 bowl", "snack", ["chhena", "milk", "sugar"]),
    ("chicken_razala", "Chicken razala", _SAVORY_CURRY_MEAT, 220, "1 bowl with gravy", "dinner", ["chicken", "yogurt-cream gravy", "spices"]),
    ("chicken_tikka", "Chicken tikka", _GRILLED_MEAT, 180, "1 plate", "dinner", ["chicken", "yogurt marinade", "tandoori spices"]),
    ("chicken_tikka_masala", "Chicken tikka masala", _SAVORY_CURRY_MEAT, 220, "1 bowl with gravy", "dinner", ["grilled chicken", "tomato-cream gravy"]),
    ("chikki", "Chikki", _SWEET_FRIED_SYRUP, 40, "2 pieces", "snack", ["jaggery", "peanuts or sesame"]),
    ("daal_baati_churma", "Daal baati churma", _THALI_MIXED, 320, "1 plate", "lunch", ["baked wheat balls", "dal", "sweet churma"]),
    ("daal_puri", "Daal puri", _BREAD_FRIED, 100, "2 pieces", "snack", ["stuffed lentil filling", "fried flatbread"]),
    ("dal_makhani", "Dal makhani", _SAVORY_CURRY_VEG, 220, "1 bowl", "dinner", ["black lentils", "kidney beans", "butter", "cream"]),
    ("dharwad_pedha", "Dharwad pedha", _SWEET_MILK_SOLID, 50, "2 pieces", "snack", ["milk solids", "sugar"]),
    ("doodhpak", "Doodhpak", _SWEET_MILK_PUDDING, 180, "1 bowl", "snack", ["milk", "rice", "sugar", "nuts"]),
    ("double_ka_meetha", "Double ka meetha", _SWEET_MILK_SOLID, 150, "1 bowl", "snack", ["fried bread", "rabri", "sugar syrup"]),
    ("dum_aloo", "Dum aloo", _SAVORY_CURRY_VEG, 200, "1 bowl", "lunch", ["baby potatoes", "gravy", "spices"]),
    ("gajar_ka_halwa", "Gajar ka halwa", _SWEET_MILK_SOLID, 150, "1 bowl", "snack", ["carrot", "milk", "ghee", "sugar"]),
    ("gavvalu", "Gavvalu", _SWEET_FRIED_SYRUP, 60, "1 small bowl", "snack", ["wheat flour", "jaggery", "fried"]),
    ("ghevar", "Ghevar", _SWEET_FRIED_SYRUP, 80, "1 piece", "snack", ["flour", "sugar syrup", "rabri topping"]),
    ("gulab_jamun", "Gulab jamun", _SWEET_FRIED_SYRUP, 80, "2 pieces", "snack", ["milk solids", "sugar syrup", "cardamom"]),
    ("imarti", "Imarti", _SWEET_FRIED_SYRUP, 60, "2 pieces", "snack", ["lentil batter", "sugar syrup"]),
    ("jalebi", "Jalebi", _SWEET_FRIED_SYRUP, 60, "3 pieces", "snack", ["refined flour batter", "sugar syrup"]),
    ("kachori", "Kachori", _SAVORY_FRIED_SNACK, 100, "2 pieces", "snack", ["stuffed lentil filling", "fried pastry"]),
    ("kadai_paneer", "Kadai paneer", _SAVORY_CURRY_VEG, 200, "1 bowl", "dinner", ["paneer", "capsicum", "onion-tomato masala"]),
    ("kadhi_pakoda", "Kadhi pakoda", _SAVORY_CURRY_VEG, 220, "1 bowl", "lunch", ["yogurt gravy", "gram flour fritters"]),
    ("kajjikaya", "Kajjikaya", _SWEET_FRIED_SYRUP, 70, "2 pieces", "snack", ["coconut-jaggery filling", "fried pastry"]),
    ("kakinada_khaja", "Kakinada khaja", _SWEET_FRIED_SYRUP, 60, "2 pieces", "snack", ["layered fried dough", "sugar syrup"]),
    ("kalakand", "Kalakand", _SWEET_MILK_SOLID, 60, "2 pieces", "snack", ["milk solids", "sugar"]),
    ("karela_bharta", "Karela bharta", _SAVORY_CURRY_VEG, 150, "1 bowl", "lunch", ["bitter gourd", "onion", "spices"]),
    ("kofta", "Kofta curry", _SAVORY_CURRY_VEG, 220, "1 bowl", "dinner", ["fried vegetable or paneer balls", "gravy"]),
    ("kuzhi_paniyaram", "Kuzhi paniyaram", _SAVORY_STEAMED, 150, "1 plate", "breakfast", ["fermented rice-lentil batter", "tempering"]),
    ("lassi", "Lassi", _DRINK_DAIRY, 250, "1 glass", "snack", ["yogurt", "sugar or salt", "spices"]),
    ("ledikeni", "Ledikeni", _SWEET_FRIED_SYRUP, 70, "2 pieces", "snack", ["khoya-stuffed chhena", "sugar syrup"]),
    ("litti_chokha", "Litti chokha", _BAKED_SNACK, 220, "1 plate", "lunch", ["baked wheat balls", "sattu filling", "mashed vegetables"]),
    ("lyangcha", "Lyangcha", _SWEET_FRIED_SYRUP, 70, "2 pieces", "snack", ["khoya", "sugar syrup"]),
    ("maach_jhol", "Maach jhol", _SAVORY_CURRY_MEAT, 220, "1 bowl with rice", "dinner", ["fish", "light curry", "vegetables"]),
    ("makki_di_roti_sarson_da_saag", "Makki di roti sarson da saag", _THALI_MIXED, 300, "1 plate", "dinner", ["cornmeal flatbread", "mustard greens curry", "butter"]),
    ("malapua", "Malapua", _SWEET_FRIED_SYRUP, 80, "2 pieces", "snack", ["flour-milk batter", "fried", "sugar syrup"]),
    ("misi_roti", "Misi roti", _BREAD_FRIED, 100, "2 pieces", "dinner", ["gram flour", "wheat flour", "spices"]),
    ("misti_doi", "Misti doi", _SWEET_MILK_PUDDING, 150, "1 bowl", "snack", ["sweetened fermented yogurt"]),
    ("modak", "Modak", _SWEET_MILK_PUDDING, 60, "2 pieces", "snack", ["rice flour dough", "coconut-jaggery filling"]),
    ("mysore_pak", "Mysore pak", _SWEET_MILK_SOLID, 50, "2 pieces", "snack", ["gram flour", "ghee", "sugar"]),
    ("navrattan_korma", "Navrattan korma", _SAVORY_CURRY_VEG, 220, "1 bowl", "dinner", ["mixed vegetables", "creamy gravy", "nuts"]),
    ("paneer_butter_masala", "Paneer butter masala", _SAVORY_CURRY_VEG, 220, "1 bowl", "dinner", ["paneer", "tomato-butter gravy", "cream"]),
    ("phirni", "Phirni", _SWEET_MILK_PUDDING, 150, "1 bowl", "snack", ["ground rice", "milk", "sugar"]),
    ("pithe", "Pithe", _SWEET_MILK_PUDDING, 100, "2 pieces", "snack", ["rice flour", "coconut-jaggery filling"]),
    ("poornalu", "Poornalu", _SWEET_FRIED_SYRUP, 70, "2 pieces", "snack", ["rice-lentil dough", "jaggery filling", "fried"]),
    ("pootharekulu", "Pootharekulu", _SWEET_MILK_SOLID, 40, "2 pieces", "snack", ["rice starch sheets", "sugar", "ghee"]),
    ("qubani_ka_meetha", "Qubani ka meetha", _SWEET_MILK_PUDDING, 150, "1 bowl", "snack", ["dried apricots", "sugar syrup", "cream"]),
    ("rabri", "Rabri", _SWEET_MILK_SOLID, 120, "1 bowl", "snack", ["reduced sweetened milk", "nuts"]),
    ("ras_malai", "Ras malai", _SWEET_MILK_PUDDING, 120, "2 pieces", "snack", ["chhena dumplings", "sweetened milk"]),
    ("rasgulla", "Rasgulla", _SWEET_MILK_PUDDING, 100, "2 pieces", "snack", ["chhena balls", "light sugar syrup"]),
    ("sandesh", "Sandesh", _SWEET_MILK_SOLID, 60, "2 pieces", "snack", ["chhena", "sugar", "cardamom"]),
    ("shankarpali", "Shankarpali", _SWEET_FRIED_SYRUP, 60, "1 small bowl", "snack", ["fried flour dough", "sugar coating"]),
    ("sheer_korma", "Sheer korma", _SWEET_MILK_PUDDING, 150, "1 bowl", "snack", ["vermicelli", "milk", "dates", "nuts"]),
    ("sheera", "Sheera", _SWEET_MILK_SOLID, 150, "1 bowl", "breakfast", ["semolina", "ghee", "sugar"]),
    ("shrikhand", "Shrikhand", _SWEET_MILK_PUDDING, 150, "1 bowl", "snack", ["strained yogurt", "sugar", "saffron"]),
    ("sohan_halwa", "Sohan halwa", _SWEET_MILK_SOLID, 60, "1 piece", "snack", ["wheat starch", "ghee", "sugar"]),
    ("sohan_papdi", "Sohan papdi", _SWEET_MILK_SOLID, 50, "1 piece", "snack", ["gram flour", "sugar", "ghee", "flaky layers"]),
    ("sutar_feni", "Sutar feni", _SWEET_FRIED_SYRUP, 60, "1 small bowl", "snack", ["fine fried vermicelli", "milk", "sugar"]),
    ("unni_appam", "Unni appam", _SWEET_FRIED_SYRUP, 60, "3 pieces", "snack", ["rice flour", "banana", "jaggery", "fried"]),
    # -- Extra classes from the "Food Classification dataset" (Indian + Western mix) --
    ("apple_pie", "Apple pie", {"calories": 260, "carbs": 34, "protein": 3, "fat": 13, "fiber": 2, "sugar": 18}, 150, "1 slice", "snack", ["apple filling", "pastry crust", "sugar", "cinnamon"]),
    ("baked_potato", "Baked potato", {"calories": 150, "carbs": 30, "protein": 4, "fat": 2, "fiber": 3, "sugar": 2}, 200, "1 potato", "lunch", ["potato", "toppings"]),
    ("chai", "Masala chai", _DRINK_DAIRY, 150, "1 cup", "snack", ["black tea", "milk", "sugar", "spices"]),
    ("cheesecake", "Cheesecake", {"calories": 320, "carbs": 26, "protein": 5, "fat": 22, "fiber": 1, "sugar": 21}, 120, "1 slice", "snack", ["cream cheese", "biscuit base", "sugar"]),
    ("chicken_curry", "Chicken curry", _SAVORY_CURRY_MEAT, 220, "1 bowl with gravy", "dinner", ["chicken", "onion-tomato gravy", "spices"]),
    ("chole_bhature", "Chole bhature", {"calories": 300, "carbs": 36, "protein": 9, "fat": 14, "fiber": 6, "sugar": 4}, 320, "1 plate", "lunch", ["spiced chickpea curry", "deep fried bread"]),
    ("crispy_chicken", "Crispy fried chicken", {"calories": 290, "carbs": 15, "protein": 20, "fat": 17, "fiber": 1, "sugar": 1}, 200, "2-3 pieces", "dinner", ["fried chicken", "breading", "spices"]),
    ("dhokla", "Dhokla", {"calories": 160, "carbs": 24, "protein": 6, "fat": 4, "fiber": 2, "sugar": 3}, 150, "1 plate", "snack", ["fermented gram flour", "steamed", "tempering"]),
    ("donut", "Donut", {"calories": 410, "carbs": 51, "protein": 5, "fat": 22, "fiber": 1, "sugar": 24}, 60, "1 donut", "snack", ["fried dough", "glaze or sugar"]),
    ("fried_rice", "Fried rice", {"calories": 190, "carbs": 30, "protein": 5, "fat": 6, "fiber": 2, "sugar": 2}, 250, "1 plate", "lunch", ["rice", "vegetables", "soy sauce", "egg or protein"]),
    ("hot_dog", "Hot dog", {"calories": 270, "carbs": 22, "protein": 11, "fat": 16, "fiber": 1, "sugar": 5}, 130, "1 hot dog", "lunch", ["sausage", "bun", "condiments"]),
    ("ice_cream", "Ice cream", {"calories": 210, "carbs": 24, "protein": 4, "fat": 11, "fiber": 0, "sugar": 21}, 100, "1 scoop", "snack", ["milk", "cream", "sugar"]),
    ("kaathi_rolls", "Kaathi roll", {"calories": 250, "carbs": 26, "protein": 12, "fat": 11, "fiber": 2, "sugar": 3}, 200, "1 roll", "lunch", ["paratha wrap", "meat or paneer filling", "chutney"]),
    ("kulfi", "Kulfi", {"calories": 250, "carbs": 26, "protein": 5, "fat": 14, "fiber": 0, "sugar": 24}, 80, "1 stick", "snack", ["reduced milk", "sugar", "nuts", "cardamom"]),
    ("momos", "Momos", _SAVORY_STEAMED, 150, "6 pieces", "snack", ["steamed dumpling", "vegetable or meat filling"]),
    ("paani_puri", "Paani puri", {"calories": 280, "carbs": 40, "protein": 5, "fat": 11, "fiber": 2, "sugar": 3}, 150, "6 pieces", "snack", ["fried puri shells", "tangy spiced water", "potato filling"]),
    ("pakode", "Pakode", _SAVORY_FRIED_SNACK, 100, "1 plate", "snack", ["gram flour batter", "vegetables", "fried"]),
    ("pav_bhaji", "Pav bhaji", {"calories": 250, "carbs": 32, "protein": 6, "fat": 11, "fiber": 4, "sugar": 5}, 300, "1 plate", "dinner", ["mashed vegetable curry", "buttered bread rolls"]),
    ("taquito", "Taquito", {"calories": 230, "carbs": 22, "protein": 9, "fat": 12, "fiber": 2, "sugar": 1}, 120, "3 pieces", "snack", ["rolled fried tortilla", "meat or cheese filling"]),
]


def _micronutrients_for(nutrition: dict) -> dict[str, float]:
    if nutrition in _MEAT_TEMPLATES:
        return _MICRO_MEAT
    if nutrition in _SWEET_TEMPLATES:
        return _MICRO_SWEET
    return _MICRO_SAVORY


for _key, _display_name, _nutrition, _grams, _label, _meal, _contents in _INDIAN_DATASET_ENTRIES:
    if _key in {profile.key for profile in FOOD_PROFILES}:
        continue
    FOOD_PROFILES.append(
        FoodProfile(
            key=_key,
            display_name=_display_name,
            portion_label=_label,
            portion_grams=float(_grams),
            nutrition_per_100g=_nutrition,
            micronutrients_per_100g=_micronutrients_for(_nutrition),
            contents=_contents,
            feature_center=_DEFAULT_CENTER,
            feature_noise=0.08,
            portion_noise=max(10.0, _grams * 0.18),
            suggested_meal_type=_meal,
        )
    )


PROFILE_BY_KEY = {profile.key: profile for profile in FOOD_PROFILES}


def humanize_label(label: str) -> str:
    parts = re.split(r"[_\-\s]+", label.strip().lower())
    words = [part for part in parts if part]
    if not words:
        return "Mixed meal"
    return " ".join(word.capitalize() for word in words)


def _contains_any(label: str, keywords: list[str]) -> bool:
    return any(keyword in label for keyword in keywords)


def profile_for_label(label: str) -> FoodProfile:
    key = label.strip().lower().replace(" ", "_").replace("-", "_")
    if key in PROFILE_BY_KEY:
        return PROFILE_BY_KEY[key]

    readable = humanize_label(label)
    lowered = readable.lower()

    if _contains_any(lowered, ["salad", "greens", "lettuce", "leaf", "veg bowl"]):
        return FoodProfile(
            key=key,
            display_name=readable,
            portion_label="1 bowl",
            portion_grams=180,
            nutrition_per_100g={"calories": 90, "carbs": 10, "protein": 4, "fat": 4, "fiber": 3, "sugar": 4},
            micronutrients_per_100g={"Vitamin A": 18, "Vitamin C": 20, "Folate": 12, "Iron": 6, "Potassium": 10},
            contents=["mixed vegetables", "greens", "seasoning"],
            feature_center=np.array([0.30, 0.62, 0.26, 0.16, 0.16, 0.18, 0.63, 0.24, 0.17, 0.34, 0.00, 0.25, 0.60, 0.60,
                                     0.19, 0.16, 0.14, 0.13, 0.18, 0.20,
                                     0.32, 0.20, 0.16, 0.14, 0.13, 0.15,
                                     0.36, 0.18, 0.14, 0.12, 0.10, 0.10], dtype=np.float32),
            feature_noise=0.07,
            portion_noise=20,
            suggested_meal_type="lunch",
        )

    if _contains_any(lowered, ["pizza"]):
        return FoodProfile(
            key=key,
            display_name=readable,
            portion_label="2 slices",
            portion_grams=210,
            nutrition_per_100g={"calories": 260, "carbs": 29, "protein": 11, "fat": 10, "fiber": 2, "sugar": 4},
            micronutrients_per_100g={"Vitamin A": 8, "Vitamin C": 10, "Calcium": 15, "Iron": 8, "Potassium": 7},
            contents=["crust", "sauce", "cheese", "toppings"],
            feature_center=np.array([0.72, 0.53, 0.37, 0.26, 0.21, 0.18, 0.56, 0.45, 0.34, 0.59, 0.27, 0.33, 0.69, 0.67,
                                     0.18, 0.15, 0.12, 0.22, 0.20, 0.13,
                                     0.35, 0.18, 0.14, 0.12, 0.11, 0.10,
                                     0.28, 0.16, 0.16, 0.17, 0.13, 0.10], dtype=np.float32),
            feature_noise=0.07,
            portion_noise=24,
            suggested_meal_type="dinner",
        )

    if _contains_any(lowered, ["burger", "sandwich", "wrap", "roll"]):
        return FoodProfile(
            key=key,
            display_name=readable,
            portion_label="1 serving",
            portion_grams=220,
            nutrition_per_100g={"calories": 225, "carbs": 24, "protein": 12, "fat": 9, "fiber": 2, "sugar": 4},
            micronutrients_per_100g={"Vitamin B3": 12, "Vitamin B12": 10, "Iron": 8, "Calcium": 7, "Potassium": 8},
            contents=["bread or bun", "protein", "vegetables", "sauce"],
            feature_center=np.array([0.58, 0.44, 0.30, 0.29, 0.22, 0.18, 0.44, 0.35, 0.28, 0.52, 0.17, 0.18, 0.57, 0.61,
                                     0.20, 0.17, 0.14, 0.18, 0.18, 0.13,
                                     0.28, 0.19, 0.15, 0.14, 0.12, 0.12,
                                     0.26, 0.17, 0.16, 0.17, 0.15, 0.10], dtype=np.float32),
            feature_noise=0.07,
            portion_noise=26,
            suggested_meal_type="lunch",
        )

    if _contains_any(lowered, ["rice", "biryani", "pulao", "fried rice", "noodle", "pasta", "ramen"]):
        return FoodProfile(
            key=key,
            display_name=readable,
            portion_label="1 plate",
            portion_grams=240,
            nutrition_per_100g={"calories": 200, "carbs": 30, "protein": 6, "fat": 6, "fiber": 2, "sugar": 2},
            micronutrients_per_100g={"Vitamin B1": 7, "Vitamin B6": 7, "Magnesium": 8, "Iron": 6, "Potassium": 8},
            contents=["grain base", "vegetables", "seasoning", "protein"],
            feature_center=np.array([0.66, 0.60, 0.48, 0.21, 0.17, 0.14, 0.52, 0.16, 0.14, 0.33, 0.10, 0.12, 0.71, 0.66,
                                     0.21, 0.18, 0.16, 0.16, 0.15, 0.14,
                                     0.25, 0.20, 0.17, 0.15, 0.13, 0.10,
                                     0.23, 0.18, 0.18, 0.17, 0.13, 0.11], dtype=np.float32),
            feature_noise=0.07,
            portion_noise=30,
            suggested_meal_type="lunch",
        )

    if _contains_any(lowered, ["egg", "omelette", "omelet"]):
        return FoodProfile(
            key=key,
            display_name=readable,
            portion_label="2 eggs",
            portion_grams=150,
            nutrition_per_100g={"calories": 150, "carbs": 2, "protein": 11, "fat": 10, "fiber": 0, "sugar": 1},
            micronutrients_per_100g={"Vitamin B12": 22, "Vitamin D": 12, "Iron": 6, "Choline": 18, "Selenium": 20},
            contents=["eggs", "onion", "tomato", "peppers"],
            feature_center=np.array([0.77, 0.69, 0.45, 0.18, 0.15, 0.14, 0.69, 0.24, 0.18, 0.38, 0.27, 0.12, 0.54, 0.60,
                                     0.20, 0.18, 0.14, 0.15, 0.19, 0.14,
                                     0.18, 0.20, 0.17, 0.14, 0.13, 0.12,
                                     0.25, 0.17, 0.16, 0.16, 0.15, 0.11], dtype=np.float32),
            feature_noise=0.06,
            portion_noise=16,
            suggested_meal_type="breakfast",
        )

    if _contains_any(lowered, ["curry", "masala", "paneer", "dal", "sabzi", "sabji", "gravy"]):
        return FoodProfile(
            key=key,
            display_name=readable,
            portion_label="1 bowl with gravy",
            portion_grams=220,
            nutrition_per_100g={"calories": 160, "carbs": 12, "protein": 8, "fat": 9, "fiber": 3, "sugar": 3},
            micronutrients_per_100g={"Iron": 10, "Vitamin A": 15, "Potassium": 9, "Calcium": 10},
            contents=["vegetables or paneer", "onion-tomato gravy", "spices"],
            feature_center=_DEFAULT_CENTER,
            feature_noise=0.08,
            portion_noise=26,
            suggested_meal_type="dinner",
        )

    if _contains_any(lowered, ["chapati", "roti", "naan", "paratha", "flatbread"]):
        return FoodProfile(
            key=key,
            display_name=readable,
            portion_label="2 pieces",
            portion_grams=100,
            nutrition_per_100g={"calories": 270, "carbs": 46, "protein": 8, "fat": 5, "fiber": 5, "sugar": 1},
            micronutrients_per_100g={"Iron": 9, "Magnesium": 10, "Potassium": 6},
            contents=["wheat or refined flour", "water", "ghee or butter"],
            feature_center=_DEFAULT_CENTER,
            feature_noise=0.06,
            portion_noise=14,
            suggested_meal_type="dinner",
        )

    if _contains_any(lowered, ["fruit", "banana", "apple", "orange", "berry", "melon"]):
        return FoodProfile(
            key=key,
            display_name=readable,
            portion_label="1 bowl",
            portion_grams=160,
            nutrition_per_100g={"calories": 70, "carbs": 17, "protein": 1, "fat": 0, "fiber": 2, "sugar": 13},
            micronutrients_per_100g={"Vitamin C": 22, "Vitamin A": 8, "Folate": 7, "Potassium": 14, "Manganese": 8},
            contents=["mixed fruit"],
            feature_center=np.array([0.64, 0.50, 0.41, 0.24, 0.21, 0.22, 0.57, 0.38, 0.24, 0.46, 0.15, 0.18, 0.66, 0.63,
                                     0.19, 0.17, 0.16, 0.14, 0.16, 0.18,
                                     0.23, 0.19, 0.16, 0.15, 0.13, 0.12,
                                     0.25, 0.18, 0.17, 0.16, 0.12, 0.10], dtype=np.float32),
            feature_noise=0.06,
            portion_noise=20,
            suggested_meal_type="snack",
        )

    return FoodProfile(
        key=key,
        display_name=readable,
        portion_label="1 serving",
        portion_grams=200,
        nutrition_per_100g={"calories": 180, "carbs": 20, "protein": 7, "fat": 7, "fiber": 3, "sugar": 5},
        micronutrients_per_100g={"Vitamin A": 10, "Vitamin C": 10, "Calcium": 8, "Iron": 7, "Potassium": 8},
        contents=["mixed ingredients", "seasoning", "protein or grain base"],
        feature_center=np.array([0.56, 0.52, 0.44, 0.21, 0.20, 0.19, 0.52, 0.26, 0.21, 0.40, 0.08, 0.10, 0.61, 0.62,
                                 0.20, 0.17, 0.16, 0.15, 0.15, 0.14,
                                 0.20, 0.18, 0.17, 0.15, 0.14, 0.13,
                                 0.21, 0.19, 0.17, 0.15, 0.13, 0.12], dtype=np.float32),
        feature_noise=0.08,
        portion_noise=28,
        suggested_meal_type="lunch",
    )
