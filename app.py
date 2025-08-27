import streamlit as st
import random
import time
from faker import Faker
from datetime import datetime
import pandas as pd
import requests
import json
import base64

# Initialize Faker
fake = Faker()

# Organization roles configuration
org_roles = {
    "ALF/SHE": [
        "ALF/SHE direct care staff",
        "ALF/SHE manager", 
        "ALF/SHE non-care staff",
        "RN"
    ],
    "ALF/SHE memory care": [
        "ALF/SHE MC direct care staff",
        "ALF/SHE MC manager",
        "ALF/SHE MC non-care staff", 
        "RN"
    ],
    "SLF": [
        "SLF direct care staff",
        "SLF non-care staff",
        "RN"
    ],
    "SLF memory care": [
        "SLF MC direct care staff",
        "SLF MC non-care staff",
        "RN"
    ],
    "SNF/ICF": [
        "SNF/ICF Direct Care Staff",
        "SNF/ICF Non-Care Staff",
        "SNF/ICF Manager",
        "SNF/ICF RA",
        "SNF/ICF IP",
        "RN"
    ],
    "SCF": [
        "SCF Direct Care Staff",
        "SCF Non-Care Staff", 
        "SCF Manager",
        "RN"
    ]
}

qualifications = [
    "High School Diploma",
    "Associate Degree", 
    "Bachelor's Degree",
    "Master's Degree",
    "PhD",
    "Registered Nurse (RN)",
    "Certified Nursing Assistant (CNA)",
    "Medical Assistant Certification",
    "Licensed Practical Nurse (LPN)"
]

class UserGenerator:
    """Class to generate user data"""
    
    def __init__(self):
        self.fake = Faker()
    
    def reset_unique(self):
        """Reset unique constraints to allow regeneration"""
        self.fake.unique.clear()
    
    def generate_user_data(self, role_type, org_name, org_types):
        """Generate data for a single user"""
        first_name = self.fake.first_name()
        last_name = self.fake.last_name()
        phone_number = self.fake.numerify("5#########")
        email = f"{first_name.lower()}.{last_name.lower()}@{org_name.replace(' ', '').lower()}.org"
        org_type = random.choice(org_types)
        prof_type = random.choice(org_roles[org_type])
        notification_pref = random.choice(["email", "sms", "both"])
        qualification = random.choice(qualifications)
        start_date = self.fake.date_between(start_date='-5y', end_date='today').isoformat()
        role_admin_or_staff = "facility_admin" if role_type == "facility_admin" else "staff"
        role_instructor = "instructor" if role_type == "instructor" else None
        
        return {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone_number": phone_number,
            "org_name": org_name,
            "org_type": org_type,
            "prof_type": prof_type,
            "notification_pref": notification_pref,
            "qualification": qualification,
            "start_date": start_date,
            "role_admin_or_staff": role_admin_or_staff,
            "role_instructor": role_instructor,
            "role_type": role_type  # For display purposes
        }

def generate_users_batch(num_employees, staff_perc, instructor_perc, 
                        facility_admin_perc, org_name, org_types):
    """Generate fake users data"""
    
    user_generator = UserGenerator()
    user_generator.reset_unique()  # Reset for fresh generation
    employees = []
    
    # Create progress indicators
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        for i in range(num_employees):
            # Determine role type based on percentages
            if i < num_employees * staff_perc:
                role_type = "staff"
            elif i < num_employees * (staff_perc + instructor_perc):
                role_type = "instructor"
            else:
                role_type = "facility_admin"
            
            # Generate user data
            user_data = user_generator.generate_user_data(role_type, org_name, org_types)
            
            # Create employee record for display
            employee = {
                "Role Type": role_type,
                "First Name": user_data["first_name"],
                "Last Name": user_data["last_name"],
                "Phone": user_data["phone_number"],
                "Email": user_data["email"],
                "Org Type": user_data["org_type"],
                "Professional Type": user_data["prof_type"],
                "Notification Preference": user_data["notification_pref"],
                "Qualification": user_data["qualification"],
                "Start Date": user_data["start_date"],
                "Role Admin/Staff": user_data["role_admin_or_staff"],
                "Role Instructor": user_data["role_instructor"],
                "DB Status": "Generated",  # Database onboarding status
                "Cognito Status": "Pending",  # Cognito onboarding status
                "Temporary Password": None,  # Store temporary password
                # Store API data separately
                "api_data": user_data
            }
            
            employees.append(employee)
            
            # Update status
            status_text.text(f"✅ Generated: {user_data['first_name']} {user_data['last_name']} ({i+1}/{num_employees})")
            
            # Update progress
            progress_bar.progress((i + 1) / num_employees)
            
            # Small delay for visual effect
            time.sleep(0.1)
                
    except Exception as e:
        st.error(f"Generation error: {str(e)}")
    
    finally:
        progress_bar.empty()
        status_text.empty()
    
    # Display final summary
    st.success(f"Generation complete! {len(employees)} employees created.")
    
    return employees

def call_api_endpoint(url, data, method="POST"):
    """Helper function to call API endpoints"""
    try:
        headers = {"Content-Type": "application/json"}
        
        if method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=30)
        else:
            response = requests.get(url, params=data, timeout=30)
        
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}

def create_credentials_file(user_data, temp_password):
    """Create a credentials file for download"""
    credentials = {
        "user_info": {
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"],
            "email": user_data["email"],
            "organization": user_data["org_name"],
            "role": user_data["role_type"]
        },
        "login_credentials": {
            "email": user_data["email"],
            "temporary_password": temp_password,
            "instructions": "Please change this password on first login"
        },
        "generated_at": datetime.now().isoformat(),
        "note": "This password will only be shown once. Please save it securely."
    }
    return json.dumps(credentials, indent=2)

def deploy_to_database(employees, org_name, org_types, api_base_url):
    """Deploy employees to database via API calls"""
    
    deployment_status = []
    total_steps = len(employees) * 2 + 2  # *2 for DB + Cognito per user, +2 for org creation and mapping
    
    # Create main progress container
    deploy_container = st.container()
    
    with deploy_container:
        st.subheader("🚀 Deployment Progress")
        
        # Main progress bar
        main_progress = st.progress(0)
        main_status = st.empty()
        current_step = 0
        
        # Step 1: Create Organization
        main_status.text("🏢 Creating organization...")
        org_data = {"org_name": org_name}
        org_response = call_api_endpoint(f"{api_base_url}/org/", org_data)
        
        if org_response["success"]:
            if org_response["data"]["status"] == 1:
                st.success(f"✅ Organization '{org_name}' created successfully (ID: {org_response['data']['org_id']})")
                deployment_status.append({
                    "step": "Organization Creation",
                    "status": "Success",
                    "message": f"Organization ID: {org_response['data']['org_id']}"
                })
            else:
                st.warning(f"⚠️ Organization '{org_name}' creation returned status 0 (may already exist)")
                deployment_status.append({
                    "step": "Organization Creation",
                    "status": "Warning",
                    "message": "Status 0 - Organization may already exist"
                })
        else:
            st.error(f"❌ Failed to create organization: {org_response['error']}")
            deployment_status.append({
                "step": "Organization Creation",
                "status": "Failed",
                "message": org_response['error']
            })
            return deployment_status
        
        current_step += 1
        main_progress.progress(current_step / total_steps)
        time.sleep(0.5)
        
        # Step 2: Create Organization Mappings
        main_status.text("🔗 Creating organization mappings...")
        mapping_data = {
            "org_name": org_name,
            "org_types": org_types
        }
        mapping_response = call_api_endpoint(f"{api_base_url}/create-org-mappings/", mapping_data)
        
        if mapping_response["success"]:
            if len(mapping_response["data"]["orgmap_ids"]) >= 1:
                st.success("✅ Organization types attached successfully")
                deployment_status.append({
                    "step": "Organization Mappings",
                    "status": "Success",
                    "message": "Organization types attached successfully"
                })
            else:
                st.success("✅ Organization types already exist")
                deployment_status.append({
                    "step": "Organization Mappings",
                    "status": "Success",
                    "message": "Organization types already exist"
                })
        else:
            st.error(f"❌ Failed to create organization mappings: {mapping_response['error']}")
            deployment_status.append({
                "step": "Organization Mappings",
                "status": "Failed",
                "message": mapping_response['error']
            })
            return deployment_status
        
        current_step += 1
        main_progress.progress(current_step / total_steps)
        time.sleep(0.5)
        
        # Step 3: Onboard Users (Database + Cognito)
        main_status.text("👥 Onboarding users...")
        user_progress_container = st.container()
        
        # Initialize session state for credentials if not exists
        if 'new_user_credentials' not in st.session_state:
            st.session_state.new_user_credentials = []
        
        # Clear previous credentials for new deployment
        st.session_state.new_user_credentials = []
        
        with user_progress_container:
            user_results = []
            
            for i, employee in enumerate(employees):
                user_data = employee["api_data"]
                
                # Step 3a: Database Onboarding
                current_step += 1
                main_status.text(f"📊 DB Onboarding: {user_data['first_name']} {user_data['last_name']} ({i+1}/{len(employees)})...")
                
                # Call onboard user API
                user_response = call_api_endpoint(f"{api_base_url}/onboard-user/", user_data)
                
                if user_response["success"] and user_response["data"]["status"] == 1:
                    st.success(f"✅ DB: {user_data['first_name']} {user_data['last_name']} onboarded successfully")
                    st.session_state.employees[i]["DB Status"] = "Deployed ✅"
                    
                    # Step 3b: Cognito Onboarding (only if DB onboarding successful)
                    current_step += 1
                    main_status.text(f"🔐 Cognito Onboarding: {user_data['first_name']} {user_data['last_name']} ({i+1}/{len(employees)})...")
                    
                    # Call Cognito onboard API
                    cognito_data = {"email": user_data["email"]}
                    cognito_response = call_api_endpoint(f"{api_base_url}/cognito/onboard", cognito_data)
                    
                    if cognito_response["success"]:
                        cognito_status = cognito_response["data"]["status"]
                        cognito_message = cognito_response["data"]["message"]
                        temp_password = cognito_response["data"].get("temporary_password")
                        
                        if cognito_status == "success":
                            st.success(f"🔐 Cognito: {user_data['first_name']} {user_data['last_name']} - New user created")
                            st.session_state.employees[i]["Cognito Status"] = "New User ✅"
                            st.session_state.employees[i]["Temporary Password"] = temp_password
                            
                            # Store credentials in session state for persistence
                            if temp_password:
                                credentials_file = create_credentials_file(user_data, temp_password)
                                credential_entry = {
                                    "name": f"{user_data['first_name']} {user_data['last_name']}",
                                    "email": user_data["email"],
                                    "password": temp_password,
                                    "credentials_file": credentials_file,
                                    "created_at": datetime.now().isoformat()
                                }
                                st.session_state.new_user_credentials.append(credential_entry)
                                
                        elif cognito_status == "exists":
                            st.info(f"ℹ️ Cognito: {user_data['first_name']} {user_data['last_name']} - User already exists")
                            st.session_state.employees[i]["Cognito Status"] = "Exists ℹ️"
                        else:
                            st.warning(f"⚠️ Cognito: {user_data['first_name']} {user_data['last_name']} - {cognito_message}")
                            st.session_state.employees[i]["Cognito Status"] = "Warning ⚠️"
                            
                        user_results.append({
                            "name": f"{user_data['first_name']} {user_data['last_name']}",
                            "db_status": "Success",
                            "cognito_status": cognito_status,
                            "message": f"DB: {user_response['data']['message']}, Cognito: {cognito_message}"
                        })
                    else:
                        st.error(f"❌ Cognito API error for {user_data['first_name']} {user_data['last_name']}: {cognito_response['error']}")
                        st.session_state.employees[i]["Cognito Status"] = "API Error ❌"
                        user_results.append({
                            "name": f"{user_data['first_name']} {user_data['last_name']}",
                            "db_status": "Success",
                            "cognito_status": "API Error",
                            "message": f"DB: {user_response['data']['message']}, Cognito: {cognito_response['error']}"
                        })
                else:
                    # DB onboarding failed, skip Cognito
                    if user_response["success"]:
                        error_msg = user_response["data"].get('message', 'Unknown error')
                        st.error(f"❌ DB: Failed to onboard {user_data['first_name']} {user_data['last_name']}: {error_msg}")
                    else:
                        error_msg = user_response['error']
                        st.error(f"❌ DB: API error for {user_data['first_name']} {user_data['last_name']}: {error_msg}")
                    
                    st.session_state.employees[i]["DB Status"] = "Failed ❌"
                    st.session_state.employees[i]["Cognito Status"] = "Skipped"
                    
                    user_results.append({
                        "name": f"{user_data['first_name']} {user_data['last_name']}",
                        "db_status": "Failed",
                        "cognito_status": "Skipped",
                        "message": error_msg
                    })
                    
                    # Skip Cognito step in progress
                    current_step += 1
                
                # Update progress
                main_progress.progress(current_step / total_steps)
                time.sleep(0.2)  # Small delay between requests
            
            deployment_status.extend(user_results)
        
        # Final status
        main_progress.progress(1.0)
        main_status.text("🎉 Deployment completed!")
        
        # Summary
        successful_db_users = sum(1 for result in user_results if result["db_status"] == "Success")
        failed_db_users = len(user_results) - successful_db_users
        new_cognito_users = sum(1 for result in user_results if result["cognito_status"] == "success")
        existing_cognito_users = sum(1 for result in user_results if result["cognito_status"] == "exists")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("✅ DB Deployed", successful_db_users)
        with col2:
            st.metric("❌ DB Failed", failed_db_users)
        with col3:
            st.metric("🆕 New Cognito Users", new_cognito_users)
        with col4:
            st.metric("📋 Existing Cognito Users", existing_cognito_users)
        
        # Final results
        if failed_db_users == 0:
            st.balloons()
            st.success("🎉 All users deployed successfully to both database and Cognito!")
        elif successful_db_users > 0:
            st.warning(f"⚠️ Partial deployment: {successful_db_users} successful, {failed_db_users} failed")
        else:
            st.error("❌ Deployment failed for all users")
    
    return deployment_status


def show_persistent_credentials():
    """Display persistent credentials section"""
    if 'new_user_credentials' in st.session_state and st.session_state.new_user_credentials:
        st.markdown("---")
        st.subheader("🔐 New User Credentials")
        st.warning("⚠️ **IMPORTANT**: Temporary passwords will only be shown once during deployment. Please save them securely!")
        
        # Show when credentials were created
        if st.session_state.new_user_credentials:
            first_cred = st.session_state.new_user_credentials[0]
            created_time = datetime.fromisoformat(first_cred['created_at'])
            st.info(f"📅 Credentials created: {created_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Add option to clear credentials
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🗑️ Clear Credentials", type="secondary"):
                st.session_state.new_user_credentials = []
                st.success("Credentials cleared!")
                st.rerun()
        
        # Show expandable sections for each new user
        for i, cred in enumerate(st.session_state.new_user_credentials):
            with st.expander(f"🔑 Credentials for {cred['name']} ({cred['email']})", expanded=i==0):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Email:** {cred['email']}")
                    st.write(f"**Name:** {cred['name']}")
                    
                    # Always show password (since it's persistent now)
                    st.write("**Temporary Password:**")
                    st.code(cred['password'], language=None)
                    st.caption("⚠️ Remember to change this password on first login!")
                
                with col2:
                    st.download_button(
                        label="📥 Download Credentials",
                        data=cred['credentials_file'],
                        file_name=f"credentials_{cred['email'].replace('@', '_').replace('.', '_')}.json",
                        mime="application/json",
                        key=f"download_{i}_{cred['email']}"
                    )
                
                with col3:
                    # Copy to clipboard functionality
                    st.write("**Actions:**")
                    if st.button(f"📋 Copy Password", key=f"copy_{i}_{cred['email']}"):
                        st.success("Password copied to display above!")
        
        # Bulk download option
        if len(st.session_state.new_user_credentials) > 1:
            st.markdown("---")
            st.subheader("📦 Bulk Download")
            
            # Create consolidated credentials file
            all_credentials = {
                "organization": st.session_state.get('last_org_name', 'Unknown'),
                "deployment_date": st.session_state.new_user_credentials[0]['created_at'],
                "total_users": len(st.session_state.new_user_credentials),
                "users": []
            }
            
            for cred in st.session_state.new_user_credentials:
                all_credentials["users"].append({
                    "name": cred['name'],
                    "email": cred['email'],
                    "temporary_password": cred['password'],
                    "instructions": "Please change this password on first login"
                })
            
            bulk_file_content = json.dumps(all_credentials, indent=2)
            
            st.download_button(
                label="📥 Download All Credentials",
                data=bulk_file_content,
                file_name=f"all_credentials_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                key="bulk_download_credentials"
            )


def display_employee_card(employee, index):
    """Display employee information in a card format"""
    
    # Determine card border color based on status
    db_status = employee.get('DB Status', 'Generated')
    cognito_status = employee.get('Cognito Status', 'Pending')
    
    if 'Deployed' in db_status and ('✅' in cognito_status or 'ℹ️' in cognito_status):
        border_color = "#28a745"  # Green - both successful
        status_color = "#28a745"
    elif 'Failed' in db_status or 'Failed' in cognito_status:
        border_color = "#dc3545"  # Red - any failure
        status_color = "#dc3545"
    elif 'API Error' in db_status or 'API Error' in cognito_status:
        border_color = "#ffc107"  # Yellow - any API error
        status_color = "#ffc107"
    else:
        border_color = "#6c757d"  # Gray - pending/generated
        status_color = "#6c757d"
    
    with st.container():
        st.markdown(f"""
        <div style="
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            background-color: #f9f9f9;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid {border_color};
        ">
            <h4 style="color: #2E86AB; margin-bottom: 10px;">
                {employee['First Name']} {employee['Last Name']}
                <span style="color: {status_color}; font-size: 12px; float: right;">
                    DB: {db_status} | Cognito: {cognito_status}
                </span>
            </h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div><strong>Role Type:</strong> {employee['Role Type']}</div>
                <div><strong>Professional Type:</strong> {employee['Professional Type']}</div>
                <div><strong>Email:</strong> {employee['Email']}</div>
                <div><strong>Phone:</strong> {employee['Phone']}</div>
                <div><strong>Org Type:</strong> {employee['Org Type']}</div>
                <div><strong>Qualification:</strong> {employee['Qualification']}</div>
                <div><strong>Notification Pref:</strong> {employee['Notification Preference']}</div>
                <div><strong>Start Date:</strong> {employee['Start Date']}</div>
                <div><strong>Role Admin/Staff:</strong> {employee['Role Admin/Staff']}</div>
                <div><strong>Role Instructor:</strong> {employee['Role Instructor'] if employee['Role Instructor'] else 'N/A'}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Show temporary password if available
        if employee.get('Temporary Password'):
            st.markdown(f"""
            <div style="margin-top: 10px; padding: 10px; background-color: #fff3cd; border-radius: 5px; border: 1px solid #ffeaa7;">
                <strong>🔐 Temporary Password Available</strong> - 
                <span style="color: #856404;">Available in credentials section below</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

def main():
    st.set_page_config(
        page_title="Demo Site Onboarding Automator", 
        page_icon="🎭", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
        .main-header {
            text-align: center;
            color: #2E86AB;
            font-size: 2.5rem;
            margin-bottom: 2rem;
            font-weight: bold;
        }
        .config-section {
            background-color: #f0f2f6;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .metric-card {
            background-color: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 10px 0;
        }
        .deploy-section {
            background-color: #e8f5e8;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #28a745;
            margin: 20px 0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-header">🎭 Fake Data Generator & Deployer</h1>', unsafe_allow_html=True)
    
    # Hardcoded API base URL
    API_BASE_URL = "http://23.22.214.208:8000"
    
    # Sidebar for information
    with st.sidebar:
        st.header("ℹ️ About")
        st.write("This tool generates fake employee data and deploys it to the test database.")
        st.write("**Features:**")
        st.write("- Generate realistic fake employee profiles")
        st.write("- Configurable role distributions")
        st.write("- Multiple organization types")
        st.write("- Deploy to database via API")
        st.write("- Cognito user creation")
        
        st.markdown("---")
        st.subheader("🔧 API Configuration")
        st.info(f"API URL: {API_BASE_URL}")
        
        st.markdown("---")
        st.subheader("📊 Quick Stats")
        if 'employees' in st.session_state:
            st.metric("Total Generated", len(st.session_state.employees))
            role_counts = {}
            db_status_counts = {}
            cognito_status_counts = {}
            for emp in st.session_state.employees:
                role = emp['Role Type']
                db_status = emp.get('DB Status', 'Generated')
                cognito_status = emp.get('Cognito Status', 'Pending')
                role_counts[role] = role_counts.get(role, 0) + 1
                db_status_counts[db_status] = db_status_counts.get(db_status, 0) + 1
                cognito_status_counts[cognito_status] = cognito_status_counts.get(cognito_status, 0) + 1
            
            st.write("**By Role:**")
            for role, count in role_counts.items():
                st.text(f"{role}: {count}")
            
            st.write("**DB Status:**")
            for status, count in db_status_counts.items():
                st.text(f"{status}: {count}")
            
            st.write("**Cognito Status:**")
            for status, count in cognito_status_counts.items():
                st.text(f"{status}: {count}")
        
        # Show credential count in sidebar
        if 'new_user_credentials' in st.session_state and st.session_state.new_user_credentials:
            st.markdown("---")
            st.subheader("🔐 Credentials")
            st.metric("New User Passwords", len(st.session_state.new_user_credentials))
    
    # Configuration Section
    st.markdown('<div class="config-section">', unsafe_allow_html=True)
    st.subheader("📋 Configuration Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        org_desired_name = st.text_input("Organization Name", value="Sunrise Senior Living")
        num_employees = st.number_input("Number of Employees", min_value=1, max_value=100, value=10)
        
        st.write("**Role Distribution:**")
        staff_perc = st.slider("Staff Percentage", min_value=0.0, max_value=1.0, value=0.5, step=0.1)
        instructor_perc = st.slider("Instructor Percentage", min_value=0.0, max_value=1.0, value=0.4, step=0.1)
        facility_admin_perc = st.slider("Facility Admin Percentage", min_value=0.0, max_value=1.0, value=0.1, step=0.1)
    
    with col2:
        st.write("**Organization Types:**")
        org_types = list(org_roles.keys())
        desired_org_types = st.multiselect(
            "Select Organization Types",
            org_types,
            default=["ALF/SHE", "ALF/SHE memory care"]
        )
        
        # Validation
        total_percentage = staff_perc + instructor_perc + facility_admin_perc
        if abs(total_percentage - 1.0) > 0.001:
            st.error(f"⚠️ Percentages must add up to 1.0. Current total: {total_percentage:.1f}")
        else:
            st.success("✅ Percentages add up to 1.0")
            
        if not desired_org_types:
            st.error("⚠️ Please select at least one organization type")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Action Buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        generate_button = st.button("🎲 Generate Data", type="primary", use_container_width=True)
    
    with col2:
        refresh_button = st.button("🔄 Refresh Data", use_container_width=True)
        
    with col3:
        clear_button = st.button("🗑️ Clear Results", use_container_width=True)
    
    with col4:
        # Deploy button - only show if employees exist
        has_employees = 'employees' in st.session_state and len(st.session_state.employees) > 0
        deploy_button = st.button(
            "🚀 Deploy to DB + Cognito", 
            disabled=not has_employees, 
            use_container_width=True,
            help="Generate data first" if not has_employees else "Deploy all employees to database and Cognito"
        )
    
    # Clear results
    if clear_button:
        if 'employees' in st.session_state:
            del st.session_state.employees
        if 'deployment_status' in st.session_state:
            del st.session_state.deployment_status
        if 'new_user_credentials' in st.session_state:
            del st.session_state.new_user_credentials
        if 'last_org_name' in st.session_state:
            del st.session_state.last_org_name
        st.success("All results and credentials cleared!")
        st.rerun()
    
    # Generate or refresh data
    if generate_button or refresh_button:
        if desired_org_types and abs(total_percentage - 1.0) <= 0.001:
            try:
                with st.spinner("Generating fake employee data..."):
                    employees = generate_users_batch(
                        num_employees, staff_perc, instructor_perc, 
                        facility_admin_perc, org_desired_name, desired_org_types
                    )
                    st.session_state.employees = employees
                    st.session_state.last_org_name = org_desired_name  # Store org name for credentials
                    # Clear previous deployment status
                    if 'deployment_status' in st.session_state:
                        del st.session_state.deployment_status
                    
                    # Force UI update to enable deploy button
                    st.rerun()
                
            except Exception as e:
                st.error(f"Generation error: {str(e)}")
        else:
            st.error("Please fix the configuration errors before generating data.")
    
    # Deploy to database
    if deploy_button and 'employees' in st.session_state and len(st.session_state.employees) > 0:
        try:
            st.markdown('<div class="deploy-section">', unsafe_allow_html=True)
            deployment_status = deploy_to_database(
                st.session_state.employees, 
                org_desired_name, 
                desired_org_types,
                API_BASE_URL
            )
            st.session_state.deployment_status = deployment_status
            st.markdown('</div>', unsafe_allow_html=True)
            
            # No need for time.sleep and rerun - credentials are now persistent
            
        except Exception as e:
            st.error(f"Deployment error: {str(e)}")
    
    # Show persistent credentials section (always visible if credentials exist)
    show_persistent_credentials()
    
    # Display generated data
    if 'employees' in st.session_state:
        st.markdown("---")
        st.subheader(f"👥 Generated Employee Data ({len(st.session_state.employees)} employees)")
        
        # Summary statistics
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        role_counts = {}
        db_status_counts = {}
        cognito_status_counts = {}
        for emp in st.session_state.employees:
            role = emp['Role Type']
            db_status = emp.get('DB Status', 'Generated')
            cognito_status = emp.get('Cognito Status', 'Pending')
            role_counts[role] = role_counts.get(role, 0) + 1
            db_status_counts[db_status] = db_status_counts.get(db_status, 0) + 1
            cognito_status_counts[cognito_status] = cognito_status_counts.get(cognito_status, 0) + 1
            
        with col1:
            st.metric("Total Employees", len(st.session_state.employees))
        with col2:
            st.metric("Staff", role_counts.get('staff', 0))
        with col3:
            st.metric("Instructors", role_counts.get('instructor', 0))
        with col4:
            st.metric("Facility Admins", role_counts.get('facility_admin', 0))
        with col5:
            st.metric("DB Deployed", db_status_counts.get('Deployed ✅', 0))
        with col6:
            st.metric("New Cognito Users", cognito_status_counts.get('New User ✅', 0))
        
        # Filter options
        st.subheader("🔍 Filter Results")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            role_filter = st.selectbox("Filter by Role", ["All"] + list(role_counts.keys()))
        with col2:
            org_type_filter = st.selectbox("Filter by Org Type", ["All"] + desired_org_types)
        with col3:
            db_status_filter = st.selectbox("Filter by DB Status", ["All"] + list(db_status_counts.keys()))
        with col4:
            cognito_status_filter = st.selectbox("Filter by Cognito Status", ["All"] + list(cognito_status_counts.keys()))
        with col5:
            show_details = st.checkbox("Show detailed view", value=True)
        
        # Apply filters
        filtered_employees = st.session_state.employees
        if role_filter != "All":
            filtered_employees = [emp for emp in filtered_employees if emp['Role Type'] == role_filter]
        if org_type_filter != "All":
            filtered_employees = [emp for emp in filtered_employees if emp['Org Type'] == org_type_filter]
        if db_status_filter != "All":
            filtered_employees = [emp for emp in filtered_employees if emp.get('DB Status', 'Generated') == db_status_filter]
        if cognito_status_filter != "All":
            filtered_employees = [emp for emp in filtered_employees if emp.get('Cognito Status', 'Pending') == cognito_status_filter]
        
        # Display results
        st.subheader(f"📋 Employee Details ({len(filtered_employees)} shown)")
        
        if show_details:
            # Detailed card view
            for i, employee in enumerate(filtered_employees):
                display_employee_card(employee, i)
        else:
            # Table view
            if filtered_employees:
                # Prepare data for table (exclude API data and temp password)
                table_data = []
                for emp in filtered_employees:
                    table_emp = {k: v for k, v in emp.items() if k not in ['api_data', 'Temporary Password']}
                    table_data.append(table_emp)
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)
        
        # Export option
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Export All to CSV"):
                # Prepare data without api_data and temporary password fields
                export_data = []
                for emp in st.session_state.employees:
                    export_emp = {k: v for k, v in emp.items() if k not in ['api_data', 'Temporary Password']}
                    export_data.append(export_emp)
                df = pd.DataFrame(export_data)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download All CSV",
                    data=csv,
                    file_name=f"employees_{org_desired_name.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        with col2:
            if st.button("📊 Export Filtered to CSV"):
                if filtered_employees:
                    # Prepare data without api_data and temporary password fields
                    export_data = []
                    for emp in filtered_employees:
                        export_emp = {k: v for k, v in emp.items() if k not in ['api_data', 'Temporary Password']}
                        export_data.append(export_emp)
                    df_filtered = pd.DataFrame(export_data)
                    csv_filtered = df_filtered.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Filtered CSV",
                        data=csv_filtered,
                        file_name=f"employees_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )


if __name__ == "__main__":
    main()