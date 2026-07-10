# Implementation Plan - LJU Semester IV Agricultural Analytics & Prediction Lab

We will upgrade the **PlantCare** platform to fully satisfy Lok Jagruti University's Semester IV syllabus requirements for *Fundamentals of Computer Science using Python - II*. 

We will build an **Intelligent Agricultural Analytics & Prediction Lab** directly integrated into the project.

---

## Proposed Changes

### 1. New Django App: `analytics`
We will create a new Django application `analytics` to house all data analysis, machine learning, deep learning, scraping, and RESTful API features.

#### [NEW] `analytics/models.py`
We will define models to store datasets and trained model runs:
* **`Dataset`**: Stores uploaded CSV files (e.g. crop yield, weather parameters) with fields for `name`, `file`, and `uploaded_at`.
* **`MLModel`**: Stores training runs and validation metrics (R², MAE, MSE, Confusion Matrix, Accuracy, Sensitivity, Specificity) and references a serialized model pickle file.

#### [NEW] `analytics/views.py`
We will implement the views mapping to the LJU syllabus units:
1. **Pandas EDA Lab (Unit 1)**: View that handles dataset upload, cleans missing values/duplicates, filters outliers, and computes basic stats (describe, shape, correlation).
2. **Visualizations (Unit 2)**: Computes interactive Plotly charts (e.g. Yield vs Year scatter, correlation heatmaps) and renders Seaborn charts (box plots, scatter plots).
3. **Machine Learning Trainer (Unit 3, 4, 5)**: Provides model training for:
   * *Regression*: Linear Regression & Polynomial Regression.
   * *Classification*: kNN, Decision Tree, Random Forest, & SVM.
   * Outputs evaluations ($R^2$, MAE, MSE, accuracy, confusion matrix, sensitivity, specificity).
4. **Deep Learning Lab (Unit 6)**: Renders a simulated training progress dashboard for a CNN (Convolutional Neural Network) and Transfer Learning image classifier using charts showing epoch losses.
5. **Web Scraper (Unit 7)**: Implements a scraping panel using BeautifulSoup to scrape article titles and product pricing from agricultural websites, allowing CSV exports of the scraped data.

#### [NEW] `analytics/serializers.py` & `analytics/api_views.py` (Unit 10)
Exposes DRF views:
* RESTful CRUD endpoints for `Dataset` and `MLModel`.
* JWT Token authentication controls for secure API access.

---

## Templates and UI Design

We will create:
* `templates/analytics_dashboard.html`: The central hub for the analytics lab.
* `templates/eda_lab.html`: Data cleaning and visualization view.
* `templates/ml_lab.html`: Training controls and evaluation metrics.
* `templates/dl_lab.html`: CNN training simulator.
* `templates/scraper_lab.html`: Web scraping tool interface.

These pages will use premium, glassmorphism card layouts, custom chart colors matching the green neon accent theme, and clear micro-animations.

---

## Verification Plan

### Automated Verification
* We will write integration tests in `analytics/tests.py` covering dataset uploading, model training calculations (R², Accuracy), and REST API endpoints.
* We will verify the entire system passes Django's test suite:
  ```bash
  python manage.py test
  ```

### Manual Verification
* Run the local server and verify:
  1. The new "AI Lab" menu link appears in the main navbar.
  2. CSV dataset uploads correctly run cleaning routines.
  3. Interactive Plotly charts render dynamically.
  4. Models train and display evaluation statistics and confusion matrices correctly.
  5. Web scraping outputs valid data to download.
