# ========================================
# EMAIL SERVICE
# File: backend/services/email_service.py
# ========================================

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import os
from datetime import datetime

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.smtp_from = os.getenv('SMTP_FROM', 'noreply@licensetracker.com')
        self.enabled = bool(self.smtp_user and self.smtp_password)
    
    def send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send an email"""
        if not self.enabled:
            print(f"⚠️  Email not configured. Would have sent to {to_email}: {subject}")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_from
            msg['To'] = to_email
            
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"✅ Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {e}")
            return False
    
    def send_license_expiry_alert(self, license_data: dict, admin_emails: List[str]) -> bool:
        """Send license expiry alert"""
        days_left = (license_data['valid_to'] - datetime.now().date()).days
        
        subject = f"⚠️ License Expiring Soon: {license_data['software_name']}"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9fafb; border-radius: 8px;">
                <h2 style="color: #f59e0b; margin-top: 0;">⚠️ License Expiring Soon</h2>
                
                <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #1f2937;">License Details:</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>License Key:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{license_data['license_key']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>Software:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{license_data['software_name']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>Expiry Date:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; color: #ef4444;">
                                <strong>{license_data['valid_to']}</strong>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 8px;"><strong>Days Remaining:</strong></td>
                            <td style="padding: 8px; color: #ef4444;">
                                <strong>{days_left} days</strong>
                            </td>
                        </tr>
                    </table>
                </div>
                
                <div style="background-color: #fef3c7; padding: 15px; border-left: 4px solid #f59e0b; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Action Required:</strong></p>
                    <p style="margin: 5px 0 0 0;">Please renew this license before it expires to avoid service disruption.</p>
                </div>
                
                <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 12px;">
                    <p>This is an automated alert from License Tracker.</p>
                    <p>Login to view more details: <a href="http://localhost:3000" style="color: #3b82f6;">License Tracker Dashboard</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        success = True
        for email in admin_emails:
            if not self.send_email(email, subject, html_body):
                success = False
        
        return success
    
    def send_overused_license_alert(self, license_data: dict, admin_emails: List[str]) -> bool:
        """Send overused license alert"""
        usage_percent = (license_data['used'] / license_data['max_usage']) * 100
        
        subject = f"🚨 License Over-Utilized: {license_data['software_name']}"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9fafb; border-radius: 8px;">
                <h2 style="color: #ef4444; margin-top: 0;">🚨 License Over-Utilized</h2>
                
                <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #1f2937;">License Details:</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>License Key:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{license_data['license_key']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>Software:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{license_data['software_name']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>Max Allowed:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{license_data['max_usage']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>Currently Used:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; color: #ef4444;">
                                <strong>{license_data['used']}</strong>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 8px;"><strong>Utilization:</strong></td>
                            <td style="padding: 8px; color: #ef4444;">
                                <strong>{usage_percent:.1f}%</strong>
                            </td>
                        </tr>
                    </table>
                </div>
                
                <div style="background-color: #fee2e2; padding: 15px; border-left: 4px solid #ef4444; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Action Required:</strong></p>
                    <p style="margin: 5px 0 0 0;">This license is over-utilized. Please purchase additional licenses or unassign devices.</p>
                </div>
                
                <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 12px;">
                    <p>This is an automated alert from License Tracker.</p>
                    <p>Login to view more details: <a href="http://localhost:3000" style="color: #3b82f6;">License Tracker Dashboard</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        success = True
        for email in admin_emails:
            if not self.send_email(email, subject, html_body):
                success = False
        
        return success
    
    def send_daily_summary(self, summary_data: dict, admin_emails: List[str]) -> bool:
        """Send daily summary report"""
        subject = f"📊 Daily Summary - {datetime.now().strftime('%B %d, %Y')}"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9fafb; border-radius: 8px;">
                <h2 style="color: #3b82f6; margin-top: 0;">📊 Daily Summary Report</h2>
                <p style="color: #6b7280;">{datetime.now().strftime('%B %d, %Y')}</p>
                
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 20px 0;">
                    <div style="background-color: white; padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 32px; font-weight: bold; color: #3b82f6;">{summary_data.get('total_devices', 0)}</div>
                        <div style="color: #6b7280; font-size: 14px;">Total Devices</div>
                    </div>
                    <div style="background-color: white; padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 32px; font-weight: bold; color: #10b981;">{summary_data.get('active_licenses', 0)}</div>
                        <div style="color: #6b7280; font-size: 14px;">Active Licenses</div>
                    </div>
                    <div style="background-color: white; padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 32px; font-weight: bold; color: #f59e0b;">{summary_data.get('expiring_soon', 0)}</div>
                        <div style="color: #6b7280; font-size: 14px;">Expiring Soon</div>
                    </div>
                    <div style="background-color: white; padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 32px; font-weight: bold; color: #ef4444;">{summary_data.get('overused', 0)}</div>
                        <div style="color: #6b7280; font-size: 14px;">Overused</div>
                    </div>
                </div>
                
                {self._generate_alerts_section(summary_data)}
                
                <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 12px;">
                    <p>This is an automated daily summary from License Tracker.</p>
                    <p>Login to view full dashboard: <a href="http://localhost:3000" style="color: #3b82f6;">License Tracker</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        success = True
        for email in admin_emails:
            if not self.send_email(email, subject, html_body):
                success = False
        
        return success
    
    def _generate_alerts_section(self, summary_data: dict) -> str:
        """Generate alerts section for email"""
        alerts = []
        
        if summary_data.get('expiring_soon', 0) > 0:
            alerts.append(f"⚠️ {summary_data['expiring_soon']} license(s) expiring within 30 days")
        
        if summary_data.get('overused', 0) > 0:
            alerts.append(f"🚨 {summary_data['overused']} license(s) are over-utilized")
        
        if not alerts:
            return """
            <div style="background-color: #d1fae5; padding: 15px; border-left: 4px solid #10b981; margin: 20px 0;">
                <p style="margin: 0;">✅ <strong>All Clear!</strong> No critical alerts today.</p>
            </div>
            """
        
        alerts_html = "<br>".join(alerts)
        return f"""
        <div style="background-color: #fef3c7; padding: 15px; border-left: 4px solid #f59e0b; margin: 20px 0;">
            <p style="margin: 0 0 10px 0;"><strong>⚠️ Alerts:</strong></p>
            <p style="margin: 0;">{alerts_html}</p>
        </div>
        """