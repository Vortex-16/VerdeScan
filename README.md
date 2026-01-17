# VerdeScan

This project aims to develop a Machine Learning and Image Processing Proof of Concept (PoC) for the Odisha Forest Department, which plants nearly 5 crore trees annually. The solution will automate the monitoring of sapling survival in irregular afforestation patches using drone imagery, replacing inefficient manual surveys.

## Project Structure

- **AI Model/**: Contains the machine learning pipeline, training scripts, and backend server.
- **Data/**: Directory for storing raw drone imagery and processed data.
- **frontend/**: visual dashboard for the system.

## Setup Instructions

1.  **Dataset Preparation**:
    - Ensure your raw drone imagery is placed in `c:\Code\VerdeScan\Data\Image`.
    - The system expects folders like `Debadihi VF` and `Benkmura VF` within this directory (or inside `Drone Data`/`Drone image` subdirectories locally).

2.  **AI System Setup**:
    - Navigate to the `AI Model` directory:
      ```bash
      cd "AI Model"
      ```
    - Run the complete setup script:
      ```bash
      python setup_complete_system.py
      ```
    - This script will automatically detect your data in `Data/Image`, train the forest monitoring model, and set up the backend.

3.  **Frontend**:
    - Navigate to `frontend` and run `npm run dev` to start the dashboard.
