# Cloud & Infrastructure Projects - Step-by-Step Guide

This README provides detailed step-by-step explanations of how I accomplished the major projects and tasks outlined in my professional experience. From deploying multi-cloud infrastructure to implementing API management, this document serves as a walkthrough of my processes and methodologies.

---

## 1️⃣ Multi-Cloud Infrastructure Automation

### **Goal:**  
Design and implement a multi-cloud infrastructure using **Terraform** for seamless deployment across **Azure**, **AWS**, and **GCP**.

### **Steps:**
1. **Infrastructure Planning:**  
   - Analyzed business requirements to determine the resource needs for multi-cloud support.
   - Identified critical services (e.g., compute, networking, and storage) across Azure, AWS, and GCP.

2. **Terraform Configuration:**
   - Created modular Terraform configurations for reusable code.
   - Wrote provider blocks for Azure (`azurerm`), AWS (`aws`), and GCP (`google`) to define resource provisioning.
   - Example snippet for a Terraform module:
     ```hcl
     provider "azurerm" {
       features {}
     }

     resource "azurerm_virtual_machine" "example" {
       name                  = "example-vm"
       location              = "East US"
       resource_group_name   = "example-resources"
       network_interface_ids = [azurerm_network_interface.example.id]
       vm_size               = "Standard_DS1_v2"

       os_disk {
         caching           = "ReadWrite"
         storage_account_type = "Standard_LRS"
       }
     }
     ```

3. **CI/CD Pipeline Integration:**
   - Set up Azure DevOps pipelines to automate the deployment process.
   - Configured the pipeline to trigger on commits to the main branch.
   - Used tools like `terraform fmt` for code validation and `terraform apply` for automated deployments.

4. **Validation & Testing:**
   - Tested deployments in isolated environments before moving to production.
   - Implemented monitoring tools like **Prometheus** and **Grafana** for visibility into resource health.

---

## 2️⃣ Automated CI/CD Pipelines

### **Goal:**  
Automate application deployment using **Azure DevOps** and **Jenkins**, reducing deployment time by 40%.

### **Steps:**
1. **Pipeline Design:**
   - Structured pipelines into distinct stages: **Build**, **Test**, and **Deploy**.
   - Defined pipeline YAML for Azure DevOps:
     ```yaml
     trigger:
       branches:
         include:
           - main

     pool:
       vmImage: 'ubuntu-latest'

     stages:
       - stage: Build
         jobs:
           - job: BuildJob
             steps:
               - task: UseDotNet@2
                 inputs:
                   packageType: sdk
                   version: '5.0.x'
               - script: dotnet build
       - stage: Deploy
         jobs:
           - job: DeployJob
             steps:
               - task: AzureCLI@2
                 inputs:
                   azureSubscription: 'MySubscription'
                   scriptType: 'bash'
                   scriptLocation: 'inlineScript'
                   inlineScript: |
                     az deployment group create --resource-group MyGroup --template-file main.bicep
     ```

2. **Automation Scripts:**
   - Used Jenkins for legacy systems by creating declarative pipelines in Jenkinsfile.
   - Integrated `Docker` to containerize applications during the build stage.

3. **Testing & Rollbacks:**
   - Implemented unit and integration tests to validate code during the build phase.
   - Added rollback procedures using Terraform to revert to the last stable state if deployments failed.

---

## 3️⃣ API Management and Integration

### **Goal:**  
Develop and manage APIs using **Azure API Management** to ensure secure and scalable integrations.

### **Steps:**
1. **API Gateway Setup:**
   - Provisioned Azure API Management service using Terraform.
   - Configured the gateway to manage traffic, handle throttling, and enforce security policies.

2. **API Development:**
   - Designed RESTful APIs for internal and external use cases using **Python** (Flask) and **Node.js**.
   - Example Python Flask API:
     ```python
     from flask import Flask, jsonify

     app = Flask(__name__)

     @app.route('/api/v1/data', methods=['GET'])
     def get_data():
         return jsonify({"message": "Data retrieved successfully"})

     if __name__ == "__main__":
         app.run(host='0.0.0.0', port=5000)
     ```

3. **Policy Implementation:**
   - Used Azure API Management policies to handle caching, rate limiting, and transformation.
   - Example of caching policy:
     ```xml
     <inbound>
         <cache-lookup vary-by-developer="false" />
     </inbound>
     ```

4. **Monitoring & Optimization:**
   - Integrated **Azure Monitor** for API performance tracking.
   - Used logs to identify bottlenecks and reduced API latency by optimizing database queries.

---

## 4️⃣ Network Infrastructure Optimization

### **Goal:**  
Enhance scalability and reduce downtime by 25% through automated network monitoring workflows.

### **Steps:**
1. **Monitoring Setup:**
   - Deployed **Azure Network Watcher** to monitor network performance.
   - Configured alerts for key metrics such as bandwidth usage and latency.

2. **Automation Tools:**
   - Wrote PowerShell and Python scripts to automate alert responses.
   - Example PowerShell script for network monitoring:
     ```powershell
     $resourceGroup = "example-group"
     $vmName = "example-vm"

     Get-AzVM -ResourceGroupName $resourceGroup -Name $vmName | Start-AzVM
     ```

3. **Load Balancer Configuration:**
   - Configured Azure Load Balancers to distribute traffic evenly and handle failovers.
   - Tuned health probes to ensure only healthy VMs received traffic.

---

## 5️⃣ Logging and Monitoring with Prometheus & Grafana

### **Goal:**  
Improve system visibility and reliability using **Prometheus** for monitoring and **Grafana** for visualization.

### **Steps:**
1. **Prometheus Setup:**
   - Deployed Prometheus as a Docker container:
     ```bash
     docker run -d --name prometheus -p 9090:9090 -v /path/to/config:/etc/prometheus prom/prometheus
     ```

2. **Metrics Collection:**
   - Configured exporters (e.g., Node Exporter) to collect system-level metrics.
   - Defined Prometheus scrape configurations in `prometheus.yml`.

3. **Grafana Dashboards:**
   - Integrated Grafana with Prometheus as the data source.
   - Created custom dashboards for CPU usage, memory usage, and API latency.

4. **Alerting:**
   - Set up Grafana alerts to notify stakeholders of threshold breaches via Slack and email.

---

## 🔧 Tools and Technologies Used
- **Cloud Platforms:** Azure, AWS, GCP  
- **Automation:** Terraform, Ansible, Azure DevOps, Jenkins  
- **Containerization:** Docker, Kubernetes  
- **Monitoring:** Prometheus, Grafana, Azure Monitor  
- **API Development:** Python, Node.js, Azure API Management  
- **Scripting:** Bash, PowerShell, Python  

---

This README consolidates the technical methodologies and step-by-step approaches I employed to deliver impactful cloud and infrastructure solutions. If you'd like more details, feel free to reach out via my [LinkedIn Profile](https://linkedin.com/in/ngubriceche).
