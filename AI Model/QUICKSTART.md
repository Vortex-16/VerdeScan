# ⚡ Quick Start Guide - Verde Scan

Get Verde Scan up and running in 5 minutes!

---

## 🚀 Super Quick Start (One Command)

```bash
python setup_complete_system.py
```

This will automatically:
- ✅ Install all dependencies
- ✅ Download the hackathon dataset
- ✅ Train the ML model
- ✅ Test the system
- ✅ Generate sample data

Then start the server:
```bash
python run_server.py
```

Visit: **http://localhost:8000**

---

## 📝 Manual Setup (5 Steps)

### 1️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 2️⃣ Download Dataset
```bash
python download_dataset.py
```

Or manually download from:
- [Drone Data](https://drive.google.com/drive/folders/1MiCG_suSBiDITGMqtTOl4-yGZ4Pz32Ob)
- [Drone Images](https://drive.google.com/drive/folders/1eyZazeGt7TFbCwBvMjWzjtvQujPp0JMx)

### 3️⃣ Train ML Model
```bash
python train_forest_model.py
```
⏱️ Takes ~20-30 minutes

### 4️⃣ Test System
```bash
python test_system.py
```

### 5️⃣ Start Server
```bash
python run_server.py
```

---

## 🐳 Docker Quick Start

```bash
# Development mode
docker-compose --profile development up

# Production mode
docker-compose --profile production up -d
```

Access: **http://localhost:8000**

---

## 🧪 Quick Test

After starting the server, test the API:

```bash
# Health check
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs
```

---

## 📊 What You Get

✅ **Trained ML Model** - ResNet50-based CNN  
✅ **REST API** - FastAPI with async processing  
✅ **Web Dashboard** - Interactive UI  
✅ **Docker Ready** - Easy deployment  
✅ **Complete Docs** - API documentation  

---

## 🎯 Key Features

- **Tree Detection**: Automatically detect trees in drone images
- **Health Classification**: Classify as Alive/Dead/Diseased
- **Batch Processing**: Process multiple images
- **Real-time Updates**: Track processing status
- **Export Results**: Download CSV reports

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `run_server.py` | Start the web server |
| `train_forest_model.py` | Train the ML model |
| `test_system.py` | Test the system |
| `download_dataset.py` | Download dataset |
| `setup_complete_system.py` | One-command setup |

---

## 🔧 Configuration

Edit `.env` file:
```env
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=development
MAX_CONCURRENT_REQUESTS=5
```

---

## 🆘 Troubleshooting

**Port already in use?**
```bash
# Change port in .env
API_PORT=8001
```

**Import errors?**
```bash
pip install -r requirements.txt
```

**Model not found?**
```bash
python train_forest_model.py
```

---

## 📚 More Information

- **Full Documentation**: See [README.md](README.md)
- **Deployment Guide**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **API Docs**: http://localhost:8000/docs (after starting server)

---

## 🎉 You're Ready!

Your forest monitoring system is now running!

**Dashboard**: http://localhost:8000  
**API Docs**: http://localhost:8000/docs  
**Health Check**: http://localhost:8000/health

---

**Need help?** Open an issue on GitHub!
