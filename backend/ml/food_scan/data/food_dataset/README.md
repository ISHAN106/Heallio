# Food scan CNN training data

Create one subfolder per food class inside this directory, named after the dish, and drop real
photos of that dish into it. Example layout:

```
data/food_dataset/
  butter_chicken/
    photo001.jpg
    photo002.jpg
    ...
  paneer_tikka/
    photo001.jpg
    ...
  pizza_slice/
    ...
  sushi/
    ...
```

Guidelines:
- Aim for **at least 80-150 photos per class**; more (300+) gives noticeably better accuracy.
  Fewer than ~40 per class will train but will overfit badly.
- Vary lighting, angle, plate/background, and portion size within each class — that variation is
  what the model needs to generalize instead of memorizing backgrounds.
- Supported formats: .jpg, .jpeg, .png, .webp, .bmp
- Folder names become the class labels. Use `snake_case` matching (or close to) the profiles
  already defined in `catalog.py` (e.g. `butter_chicken`, `biryani`, `dosa`, `pasta_bolognese`,
  `steak`) so nutrition data resolves exactly. Unrecognized names still work — `profile_for_label`
  will fall back to a reasonable keyword-based nutrition estimate — but exact matches are best.
- You can freely mix Indian and Western classes in the same folder tree; the trainer discovers
  classes automatically from whatever subfolders exist.

Once photos are in place, install the new deps and train:

```
cd backend
pip install -r requirements.txt
python -m ml.food_scan.train_cnn
```

This writes:
- `model/food_scan_cnn.pt` — the trained weights
- `model/food_scan_cnn_classes.json` — the class list (index -> label)
- `model/food_scan_cnn_training_report.json` — validation accuracy / portion MAE

The backend automatically prefers the CNN the moment those files exist (see
`cnn_artifacts_available()` in `cnn.py`); no other code changes are needed. Delete
`model/food_scan_cnn.pt` to fall back to the older RandomForest model.
