@echo off
echo 🧹 Cleaning up Verde Scan Codebase...

echo 🗑️ Deleting Verification Scripts...
del "AI Model\test_monitor_logic.py"
del "AI Model\verify_model_robustness.py"
del "AI Model\test_real_inference.py"
del "AI Model\test_prediction.py"
del "AI Model\prove_survival_logic.py"
del "AI Model\scale_test_survival.py"

echo 🗑️ Deleting Old/Unused Tests...
del "AI Model\test_benchmark.py"
del "AI Model\test_system.py"
del "AI Model\train_models.py" 
REM Keeping train_forest_model.py as it is the current working one

echo 🗑️ Deleting Setup Logic (System is already set up)...
del "AI Model\setup_complete_system.py"
del "AI Model\download_dataset.py"
del "AI Model\push_to_github.sh"

echo 🗑️ Deleting Incompatible Scripts...
del "AI Model\run.sh"

echo ✅ Cleanup Complete!
pause
