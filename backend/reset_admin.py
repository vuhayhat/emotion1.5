from app import app, db, User

with app.app_context():
    # Update existing admin2 account if exists
    admin = User.query.filter_by(username='admin2').first()
    if admin:
        print("Updating existing admin2 account...")
        admin.set_password('admin123')
        db.session.commit()
        print("Admin2 password updated successfully!")
    else:
        # Create new admin2 account if it doesn't exist
        new_admin = User(
            username='admin2',
            email='admin@example.com',
            role='admin',
            full_name='Administrator',
            is_active=True
        )
        new_admin.set_password('admin123')
        db.session.add(new_admin)
        db.session.commit()
        print("Admin2 account created successfully!")
    
    # Verify the account
    admin = User.query.filter_by(username='admin2').first()
    print(f"Verification: admin2 account exists = {admin is not None}")
    if admin:
        print(f"Username: {admin.username}")
        print(f"Role: {admin.role}")
        print(f"Is active: {admin.is_active}")
        # Test password
        test_password = 'admin123'
        password_correct = admin.check_password(test_password)
        print(f"Password verification test: {'Success' if password_correct else 'Failed'}") 