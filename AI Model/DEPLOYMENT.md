# 🚀 Deployment Guide - Verde Scan

Complete deployment instructions for the Verde Scan forest monitoring system.

---

## 📋 Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Training the ML Model](#training-the-ml-model)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Cloud Deployment](#cloud-deployment)
6. [Troubleshooting](#troubleshooting)

---

## 🖥️ Local Development Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager
- 8GB+ RAM recommended
- GPU optional (for faster training)

### Step-by-Step Setup

1. **Clone the Repository**
```bash
git clone https://github.com/PyRaghaw/verde_scan.git
cd verde_scan
```

2. **Create Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Create Required Directories**
```bash
mkdir -p ml_models hackathon_dataset data logs static/proof_images
```

---

## 🤖 Training the ML Model

### Download Dataset

**Option 1: Automatic Download**
```bash
python download_dataset.py
```

**Option 2: Manual Download**
1. Download [Drone Data](https://drive.google.com/drive/folders/1MiCG_suSBiDITGMqtTOl4-yGZ4Pz32Ob)
2. Download [Drone Images](https://drive.google.com/drive/folders/1eyZazeGt7TFbCwBvMjWzjtvQujPp0JMx)
3. Extract to:
   - `hackathon_dataset/drone_data/`
   - `hackathon_dataset/drone_images/`

### Train the Model

```bash
# Full training (30 epochs, ~20-30 minutes)
python train_forest_model.py

# Quick training (10 epochs, ~10 minutes)
python train_forest_model.py --epochs 10

# With GPU acceleration
CUDA_VISIBLE_DEVICES=0 python train_forest_model.py
```

### Verify Training

```bash
# Check if model was created
ls -lh ml_models/forest_model.pth

# View training metrics
cat ml_models/training_history.json

# View training curves
open ml_models/training_curves.png  # macOS
xdg-open ml_models/training_curves.png  # Linux
```

---

## 🐳 Docker Deployment

### Build Docker Image

```bash
# Build the image
docker build -t verde-scan:latest .

# Verify build
docker images | grep verde-scan
```

### Run with Docker Compose

**Development Mode:**
```bash
docker-compose --profile development up
```

**Production Mode:**
```bash
docker-compose --profile production up -d
```

**View Logs:**
```bash
docker-compose logs -f verde-scan-prod
```

**Stop Services:**
```bash
docker-compose down
```

### Docker Environment Variables

Create `docker.env`:
```env
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=production
MAX_CONCURRENT_REQUESTS=10
LOG_LEVEL=INFO
```

Run with custom env:
```bash
docker-compose --env-file docker.env up
```

---

## 🌐 Production Deployment

### System Requirements

**Minimum:**
- 2 CPU cores
- 4GB RAM
- 20GB storage
- Ubuntu 20.04+ or similar

**Recommended:**
- 4+ CPU cores
- 8GB+ RAM
- 50GB+ SSD storage
- GPU for faster processing

### Production Setup

1. **Update System**
```bash
sudo apt update && sudo apt upgrade -y
```

2. **Install Docker**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

3. **Install Docker Compose**
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

4. **Clone and Configure**
```bash
git clone https://github.com/PyRaghaw/verde_scan.git
cd verde_scan
cp .env.example .env
# Edit .env for production settings
```

5. **Deploy**
```bash
docker-compose --profile production up -d
```

6. **Setup Nginx (Optional)**
```bash
sudo apt install nginx
sudo cp nginx.conf /etc/nginx/sites-available/verde-scan
sudo ln -s /etc/nginx/sites-available/verde-scan /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

7. **Setup SSL (Optional)**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Monitoring

**Check Service Status:**
```bash
docker-compose ps
```

**View Logs:**
```bash
docker-compose logs -f --tail=100
```

**Resource Usage:**
```bash
docker stats
```

**Health Check:**
```bash
curl http://localhost:8000/health
```

---

## ☁️ Cloud Deployment

### AWS EC2

1. **Launch EC2 Instance**
   - AMI: Ubuntu 20.04 LTS
   - Instance Type: t3.medium or larger
   - Storage: 30GB+ EBS
   - Security Group: Allow ports 22, 80, 443, 8000

2. **Connect and Setup**
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

3. **Follow Production Setup** (see above)

4. **Configure Security Group**
   - Inbound: HTTP (80), HTTPS (443), Custom TCP (8000)
   - Outbound: All traffic

### Google Cloud Platform

1. **Create Compute Engine Instance**
```bash
gcloud compute instances create verde-scan \
  --machine-type=n1-standard-2 \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB
```

2. **SSH and Setup**
```bash
gcloud compute ssh verde-scan
```

3. **Follow Production Setup**

### DigitalOcean

1. **Create Droplet**
   - Image: Ubuntu 20.04
   - Plan: Basic ($12/month or higher)
   - Datacenter: Nearest to users

2. **SSH and Setup**
```bash
ssh root@your-droplet-ip
```

3. **Follow Production Setup**

---

## 🔧 Troubleshooting

### Common Issues

**1. Port Already in Use**
```bash
# Find process using port 8000
lsof -i :8000
# Kill process
kill -9 <PID>
```

**2. Permission Denied**
```bash
# Fix permissions
chmod +x run_server.py test_system.py
chmod -R 755 data/ static/
```

**3. Out of Memory**
```bash
# Reduce concurrent requests in .env
MAX_CONCURRENT_REQUESTS=2
```

**4. Model Not Found**
```bash
# Retrain model
python train_forest_model.py
# Or download pre-trained model (if available)
```

**5. Docker Build Fails**
```bash
# Clean Docker cache
docker system prune -a
# Rebuild
docker-compose build --no-cache
```

**6. Import Errors**
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

### Debug Mode

**Enable Debug Logging:**
```bash
LOG_LEVEL=DEBUG python run_server.py
```

**Test Individual Components:**
```bash
# Test imports
python -c "from core.forest_processor import ForestMLProcessor; print('OK')"

# Test ML model
python -c "from ml_models.forest_detection_model import TreeDetectionModel; print('OK')"

# Run system tests
python test_system.py
```

### Performance Optimization

**1. Enable GPU (if available)**
```bash
# Check GPU availability
python -c "import torch; print(torch.cuda.is_available())"

# Install CUDA-enabled PyTorch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

**2. Optimize Worker Processes**
```bash
# In run_server.py or docker-compose.yml
uvicorn api.main:app --workers 4
```

**3. Enable Caching**
```bash
# Add to .env
ENABLE_CACHE=true
CACHE_TTL=3600
```

---

## 📊 Monitoring and Maintenance

### Log Management

**View Logs:**
```bash
tail -f logs/verde_scan.log
```

**Rotate Logs:**
```bash
# Add to crontab
0 0 * * * find logs/ -name "*.log" -mtime +7 -delete
```

### Backup

**Backup Data:**
```bash
tar -czf backup-$(date +%Y%m%d).tar.gz data/ ml_models/
```

**Restore Data:**
```bash
tar -xzf backup-20260117.tar.gz
```

### Updates

**Update Code:**
```bash
git pull origin main
docker-compose down
docker-compose --profile production up -d --build
```

**Update Dependencies:**
```bash
pip install --upgrade -r requirements.txt
```

---

## 🎯 Production Checklist

- [ ] Environment variables configured
- [ ] ML model trained and tested
- [ ] Docker containers running
- [ ] Nginx configured (if using)
- [ ] SSL certificate installed (if using)
- [ ] Firewall rules configured
- [ ] Monitoring setup
- [ ] Backup strategy in place
- [ ] Log rotation configured
- [ ] Health checks passing
- [ ] API documentation accessible
- [ ] Dashboard loading correctly

---

## 📞 Support

For deployment issues:
1. Check logs: `docker-compose logs -f`
2. Run system tests: `python test_system.py`
3. Review this guide
4. Open GitHub issue with details

---

**Happy Deploying! 🚀**
