# Methodology

## 1. Data Collection & Preparation

The dashboard is built on HR datasets stored in Excel files. A centralized data pipeline ensures consistency and usability of the data.

Data loading handled via a dedicated DataManager service
Cleaning and preprocessing (missing values, formatting, normalization)
Standardization of categorical variables (entities, roles, demographics)
Structuring into optimized pandas DataFrames

## 2. Modular Architecture (Post-Refactor)

The application follows a modular and scalable architecture after refactoring (split design), improving maintainability and clarity.

Core structure:

config/ → Global settings and business rules
services/ → Data logic and processing layer
ui/ → Layout and reusable visual components
callbacks/ → Interaction and dynamic behavior
assets/ → Styling (themes, CSS)

This separation enforces a clear distinction between data, logic, and presentation layers.

## 3. Data Management & Performance Optimization

To ensure responsiveness with large datasets:

Centralized data access via data_manager.py
Use of caching mechanisms (Flask-Caching)
Avoidance of redundant computations inside callbacks
Schema-based dynamic processing via schema_service.py

Goal: minimize latency and improve scalability

## 4. Dynamic Schema & Flexibility

A schema-driven approach enables the dashboard to adapt dynamically to different datasets.

Automatic column detection
Dynamic generation of dropdown options
Flexible filtering logic based on available fields

This allows the tool to be dataset-agnostic and reusable

## 5. UI Component Design

The interface is built using reusable and composable components:

filters.py → dynamic filtering blocks
kpis.py → KPI tiles and helpers
graphs.py → generic chart builders

Design principles:

Reusability
Readability
Separation of concerns

## 6. Interactive Logic (Callbacks)

All interactivity is handled through dedicated callback modules:

Tab-specific logic (global_tab, viz_tab, time_tab, etc.)
Dynamic updates of graphs and KPIs
Sidebar and theme management
Real-time filtering and dependency handling

This structure ensures clean and maintainable callback logic

## 7. Data Visualization Strategy

Visualizations are designed for clarity and analytical value:

Bar charts → comparisons
Pie charts → distributions
Treemaps → hierarchical insights
Time series → trend analysis

Built with Plotly for interactivity and responsiveness.

## 8. Advanced Filtering System

A flexible filtering system enables deep data exploration:

Multi-dimensional filters (entity, category, demographics…)
Conditional dependencies between filters
Context-aware filtering (based on active tab)

This supports granular and user-driven analysis

## 9. KPI & Business Logic Layer

Key metrics are computed through centralized logic:

Workforce totals
Distribution breakdowns
Demographic insights

KPI generation is standardized to ensure:

Consistency
Reusability
Easy extension

## 10. User Experience & Theming

The dashboard includes UI/UX enhancements:

Tab-based navigation
Light / Dark mode (day.css, night.css)
Clean and responsive layout

Focus: intuitive exploration and readability

## 11. Iterative Development & Refactoring

The project evolved through multiple iterations, culminating in a structured refactor:

Progressive feature additions
Performance improvements
Transition to modular architecture (split design)

This reflects a continuous improvement approach

## 12. Analytical Purpose

This dashboard is designed to support data-driven HR decision-making by:

Providing a global workforce overview
Enabling detailed segmentation
Highlighting trends and patterns
