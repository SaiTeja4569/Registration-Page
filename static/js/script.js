// Frontend script for User Authentication System
// Handles real-time validation, password strength indicators, and asynchronous API form submission.

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const registerForm = document.getElementById('register-form');
    const loginForm = document.getElementById('login-form');
    const alertsContainer = document.getElementById('alerts-container');

    // Setup Alerts utility
    const showAlert = (message, type = 'success', duration = 5000) => {
        if (!alertsContainer) return;
        
        const alert = document.createElement('div');
        alert.className = `alert ${type}`;
        
        alert.innerHTML = `
            <div class="alert-content">${escapeHTML(message)}</div>
            <button class="alert-close" type="button">&times;</button>
        `;
        
        alertsContainer.appendChild(alert);
        
        // Setup close button
        alert.querySelector('.alert-close').addEventListener('click', () => {
            alert.remove();
        });
        
        // Auto remove
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s ease';
            setTimeout(() => alert.remove(), 500);
        }, duration);
    };

    const escapeHTML = (str) => {
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag] || tag)
        );
    };

    // Client-side Registration Validation Logic
    if (registerForm) {
        const passwordInput = document.getElementById('password');
        const confirmPasswordInput = document.getElementById('confirm_password');
        const emailInput = document.getElementById('email');
        const mobileInput = document.getElementById('mobile');
        
        const passwordMeter = document.querySelector('.password-meter');
        const passwordMeterBar = document.querySelector('.password-meter-bar');
        const passwordRequirements = document.querySelector('.password-requirements');
        
        // Requirements list items
        const reqLength = document.getElementById('req-length');
        const reqUpper = document.getElementById('req-uppercase');
        const reqLower = document.getElementById('req-lowercase');
        const reqNumber = document.getElementById('req-number');
        const reqSpecial = document.getElementById('req-special');

        // Email validation pattern
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        // Mobile validation pattern (exactly 10 digits)
        const mobileRegex = /^\d{10}$/;

        // Show/hide requirement tips on password focus
        passwordInput.addEventListener('focus', () => {
            passwordMeter.style.display = 'block';
            passwordRequirements.style.display = 'block';
        });

        // Real-time password validation and strength meter
        passwordInput.addEventListener('input', () => {
            const val = passwordInput.value;
            let metCount = 0;

            // 1. Length (>= 8)
            const hasLength = val.length >= 8;
            updateRequirementUI(reqLength, hasLength);
            if (hasLength) metCount++;

            // 2. Uppercase
            const hasUpper = /[A-Z]/.test(val);
            updateRequirementUI(reqUpper, hasUpper);
            if (hasUpper) metCount++;

            // 3. Lowercase
            const hasLower = /[a-z]/.test(val);
            updateRequirementUI(reqLower, hasLower);
            if (hasLower) metCount++;

            // 4. Number
            const hasNumber = /[0-9]/.test(val);
            updateRequirementUI(reqNumber, hasNumber);
            if (hasNumber) metCount++;

            // 5. Special character
            const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(val);
            updateRequirementUI(reqSpecial, hasSpecial);
            if (hasSpecial) metCount++;

            // Update strength bar
            const percent = (metCount / 5) * 100;
            passwordMeterBar.style.width = `${percent}%`;

            // Adjust color based on strength
            if (metCount <= 2) {
                passwordMeterBar.style.backgroundColor = '#ef4444'; // Red
            } else if (metCount <= 4) {
                passwordMeterBar.style.backgroundColor = '#f59e0b'; // Orange
            } else {
                passwordMeterBar.style.backgroundColor = '#10b981'; // Green
            }
            
            validateField(passwordInput, metCount === 5, 'Password must meet all complexity requirements');
            
            // Check confirm matching as well
            if (confirmPasswordInput.value) {
                validatePasswordMatch();
            }
        });

        // Real-time Confirm Password Validation
        confirmPasswordInput.addEventListener('input', validatePasswordMatch);
        
        function validatePasswordMatch() {
            const match = passwordInput.value === confirmPasswordInput.value;
            validateField(confirmPasswordInput, match, 'Passwords do not match');
            return match;
        }

        // Real-time Email validation
        emailInput.addEventListener('input', () => {
            const isValid = emailRegex.test(emailInput.value);
            validateField(emailInput, isValid, 'Please enter a valid email address');
        });

        // Real-time Mobile validation
        mobileInput.addEventListener('input', () => {
            // Prevent entering non-numeric chars
            mobileInput.value = mobileInput.value.replace(/\D/g, '');
            const isValid = mobileRegex.test(mobileInput.value);
            validateField(mobileInput, isValid, 'Mobile number must be exactly 10 digits');
        });

        // Utility to toggle CSS validation styles
        function validateField(inputElement, isValid, errorText) {
            const errorElement = document.getElementById(`${inputElement.id}-error`);
            if (inputElement.value === '') {
                inputElement.classList.remove('valid', 'invalid');
                if (errorElement) errorElement.style.display = 'none';
                return;
            }

            if (isValid) {
                inputElement.classList.remove('invalid');
                inputElement.classList.add('valid');
                if (errorElement) errorElement.style.display = 'none';
            } else {
                inputElement.classList.remove('valid');
                inputElement.classList.add('invalid');
                if (errorElement) {
                    errorElement.textContent = errorText;
                    errorElement.style.display = 'block';
                }
            }
        }

        function updateRequirementUI(element, isMet) {
            if (isMet) {
                element.classList.remove('unmet');
                element.classList.add('met');
                element.querySelector('.status-icon').textContent = '✓';
            } else {
                element.classList.remove('met');
                element.classList.add('unmet');
                element.querySelector('.status-icon').textContent = '•';
            }
        }

        // Registration form submit handler
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const fullName = document.getElementById('fullname').value.trim();
            const email = emailInput.value.trim();
            const mobile = mobileInput.value.trim();
            const username = document.getElementById('username').value.trim();
            const password = passwordInput.value;
            const confirmPassword = confirmPasswordInput.value;

            // Final pre-submit checks
            if (!fullName || !email || !mobile || !username || !password || !confirmPassword) {
                showAlert('All fields are required.', 'error');
                return;
            }

            if (!emailRegex.test(email)) {
                showAlert('Please enter a valid email address.', 'error');
                return;
            }

            if (!mobileRegex.test(mobile)) {
                showAlert('Mobile number must be exactly 10 digits.', 'error');
                return;
            }

            // Password strength check
            const hasUpper = /[A-Z]/.test(password);
            const hasLower = /[a-z]/.test(password);
            const hasNumber = /[0-9]/.test(password);
            const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
            if (password.length < 8 || !hasUpper || !hasLower || !hasNumber || !hasSpecial) {
                showAlert('Password does not meet validation criteria.', 'error');
                return;
            }

            if (password !== confirmPassword) {
                showAlert('Password and Confirm Password must match.', 'error');
                return;
            }

            // Submit data to server using fetch
            const submitBtn = registerForm.querySelector('.submit-btn');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Registering...';

            try {
                const formData = new FormData(registerForm);
                const csrfToken = formData.get('csrf_token');

                const response = await fetch('/api/register', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken
                    },
                    body: formData
                });

                const data = await response.json();
                
                if (response.ok && data.success) {
                    showAlert(data.message, 'success');
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 1500);
                } else {
                    showAlert(data.message || 'Registration failed.', 'error');
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Register';
                }
            } catch (err) {
                console.error('Registration Error:', err);
                showAlert('An unexpected server error occurred. Please try again.', 'error');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Register';
            }
        });
    }

    // Login Form logic
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const usernameOrEmail = document.getElementById('username_or_email').value.trim();
            const password = document.getElementById('password').value;

            if (!usernameOrEmail || !password) {
                showAlert('All fields are required.', 'error');
                return;
            }

            const submitBtn = loginForm.querySelector('.submit-btn');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Signing In...';

            try {
                const formData = new FormData(loginForm);
                const csrfToken = formData.get('csrf_token');

                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken
                    },
                    body: formData
                });

                const data = await response.json();
                
                if (response.ok && data.success) {
                    showAlert(data.message, 'success');
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 1000);
                } else {
                    showAlert(data.message || 'Invalid username/email or password.', 'error');
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Sign In';
                }
            } catch (err) {
                console.error('Login Error:', err);
                showAlert('An unexpected server error occurred. Please try again.', 'error');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Sign In';
            }
        });
    }
});
