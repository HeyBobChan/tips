# Tips Management System

A comprehensive web application for managing restaurant tips, worker hours, and compensation. The system is bilingual (Hebrew/English) and supports multiple restaurants with different compensation models.

## Core Features

### 1. Restaurant Management
- Multi-restaurant support with unique configurations
- Restaurant-specific settings:
  - Base hourly rate
  - Saturday rate multiplier
  - Compensation type (standard/additive)
  - Tips threshold configuration
  - Layout type (open/closed)

### 2. Worker Portal (`/[restaurant_id]/worker-portal`)
- Worker login system
- Time tracking functionality:
  - Clock in/out capability
  - Current status display
  - Manual hours entry
- Features:
  - Date selection
  - Hours and minutes input
  - Automatic worker list synchronization

### 3. Main Tips Interface (`/[restaurant_id]/`)
- Work hours entry
- Tips entry (cash and credit)
- Daily summaries
- Monthly summaries
- Data export to CSV
- Bilingual interface (Hebrew/English)

### 4. Admin Panel (`/[restaurant_id]/admin`)
- Restaurant configuration management
- Worker management:
  - Add/remove workers
  - Set individual base wages
  - Override default hourly rates
- System settings customization

### 5. Priority Assistant (`/priority/`)
- AI-powered chat interface
- Image upload support
- Conversation history
- Specialized Priority software assistance

## Technical Details

### Backend
- Flask-based Python server
- MongoDB database integration
- Session management
- RESTful API endpoints

### Frontend
- Modern responsive design using Tailwind CSS
- Dynamic JavaScript interface
- Real-time updates
- CSV export functionality

## Current Issues

1. **Worker Time Tracking**
   - No validation for overlapping shifts
   - Manual entry could allow duplicate entries
   - No automatic break calculation

2. **Data Validation**
   - Limited input validation on the frontend
   - No comprehensive error handling for edge cases
   - Missing data consistency checks

3. **User Experience**
   - No mobile-optimized views
   - Limited offline functionality
   - No real-time notifications

4. **Security**
   - Basic session management
   - No role-based access control
   - Limited audit logging

## Suggested Improvements

### Immediate Priorities

1. **Data Integrity**
   - Implement comprehensive input validation
   - Add data consistency checks
   - Create audit logs for critical operations

2. **User Experience**
   - Add mobile-responsive design
   - Implement real-time updates
   - Add loading states and better error messages

3. **Security**
   - Implement proper authentication system
   - Add role-based access control
   - Secure API endpoints

### Future Enhancements

1. **Advanced Features**
   - Automatic shift scheduling
   - Integration with POS systems
   - Advanced reporting and analytics
   - Employee performance metrics

2. **Technical Improvements**
   - Implement WebSocket for real-time updates
   - Add offline support with PWA
   - Implement automated testing
   - Add backup and restore functionality

3. **User Interface**
   - Dark mode support
   - Customizable dashboards
   - Advanced filtering and search
   - Interactive data visualizations

## Nice-to-Have Features

1. **Integration**
   - Payroll system integration
   - Tax reporting capabilities
   - Employee scheduling system
   - Mobile app version

2. **Analytics**
   - Predictive scheduling
   - Revenue forecasting
   - Employee performance metrics
   - Custom report builder

3. **Automation**
   - Automatic tip distribution
   - Shift reminders
   - Break time tracking
   - Overtime calculations

4. **Communication**
   - In-app messaging
   - Shift swap requests
   - Announcement system
   - Employee feedback system 