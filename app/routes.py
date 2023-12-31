import os
import logging
from flask import render_template, flash, redirect, url_for, request, session
from flask_login import current_user, login_user, login_required, logout_user
from flask_mail import Message
from app.forms import PostForm, RegistrationForm, LoginForm
from werkzeug.utils import secure_filename
from app.models import Post, User
from app import app, db, bcrypt, mail
from app.utilities import load_estate_data, load_blog_data, featuring_data, perform_search, perform_filtering, get_form_data

exclusion_strings = ['101evler-cache/user_profile_crop/agent-profile/crop/', 'https://www.101evler.com/v4/images/abstract-user-1.svg',
                     '/101evler-cache/user-logo-svg/', 'www.101evler.com/v4/images/cancel_1.svg']


@app.route('/send_email', methods=['POST'])
def send_email() -> str:
    try:
        email: str = request.form['email']
        subject: str = request.form['subject']
        message: str = request.form['message']

        msg: str = Message(subject, sender=email,
                           recipients=['hnengare@gmail.com'])
        msg.body: str = message
        mail.send(msg)
        flash('Enquiry placed successfully', 'success')
        return "Sent"
    except Exception as e:
        flash(f'An error occurred while sending the email: {str(e)}', 'error')
        return "Error"


@app.route('/search', methods=['POST', 'GET'])
def search():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = request.form.get('query')
    last_hit = request.args.get('last_hit')

    if query:
        response = perform_search(query, page, per_page, last_hit)
        logging.info(response)

        if response:
            total_hits = response['hits']['total']['value']
            hits = response['hits']['hits']
            last_hit = hits[-1]['_id']

            unique_hits = {}
            for hit in hits:
                ad_no = hit['_source']['Listing Number']
                if ad_no not in unique_hits:
                    unique_hits[ad_no] = hit

            total_hits = len(unique_hits)
            hits = list(unique_hits.values())

            temp = []

            for item in hits:
                item['_source']['Images'] = [url for url in item['_source']['Images'] if all(
                    substring not in url for substring in exclusion_strings)]
                temp.append(item)

            hits = temp

            total_pages = total_hits // per_page
            if total_hits % per_page > 0:
                total_pages += 1

            return render_template('search_results.html', hits=hits, total_hits=total_hits, total_pages=total_pages, current_page=page, last_hit=last_hit)

    return redirect(url_for('home_page'))

@app.route('/')
def home_page() -> str:
    blogs_ = load_blog_data()

    blogs = list()

    for blog in blogs_:
        if blog['Image Cover']:
            blogs.append(blog)

    return render_template('landing_page.html', blogs=blogs)

# Services section route


@app.route('/#service')
def services() -> str:
    '''Render the services section'''
    return render_template('landing_page.html')

# About section route

@app.route("/register", methods=['GET', 'POST'])
def register() -> str:
    '''Register a new user'''
    if current_user.is_authenticated:
        return redirect(url_for('properties'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(
            form.password.data).decode('utf-8')
        user = User(username=form.username.data,
                    email=form.email.data,
                    password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# Login route


@app.route("/login", methods=['GET', 'POST'])
def login():
    '''Login an existing user'''
    if current_user.is_authenticated:
        return redirect(url_for('properties'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('properties'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', form=form)

# Add listing route


@app.route('/add-listing', methods=['POST', 'GET'])
@login_required
def add_listing():
    '''Add a new property listing'''
    form = PostForm()

    if "file_urls" not in session:
        session['file_urls'] = []
    file_urls = session['file_urls']

    if request.method == 'POST':
        try:
            for uploaded_file in request.files.getlist('file'):
                filename = secure_filename(uploaded_file.filename)
                if filename != '':
                    file_ext = os.path.splitext(filename)[1]
                    if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                        flash('Invalid Image', 'danger')
                        return redirect(url_for('add_listing'))
                    uploaded_file.save(os.path.join(
                        app.config['UPLOAD_PATH'], filename))
                    file_path = os.path.join(
                        app.config['UPLOAD_PATH'], filename)
                    file_urls.append(file_path)

            session['file_urls'] = file_urls

            if form.validate_on_submit():
                post = Post(file_path=str(file_urls),
                            title=form.title.data,
                            rent=form.rent.data,
                            location=form.location.data,
                            phone=form.phone.data, whatsapp=form.whatsapp.data, description=form.description.data,
                            bedrooms=form.bedrooms.data, bathrooms=form.bathrooms.data, area=form.area.data, author=current_user,
                            status=form.status.data,
                            furnishes=form.furnishes.data,
                            rooms=form.rooms.data,
                            outside_features=form.outside_features.data)

                try:
                    db.session.add(post)
                    db.session.commit()
                    flash('Property Enlisted!', 'success')
                    session.pop('file_urls', None)
                    return redirect(url_for('properties'))
                except Exception as e:
                    db.session.rollback()
                    flash(
                        'An error occurred while enlisting the property. Please try again.', 'danger')
                    print(str(e))

        except Exception as e:
            flash(
                f'Error occurred while processing the request: {e}', 'danger')

    return render_template('add_listing.html', form=form)


@app.route('/properties', methods=['POST', 'GET'])
def properties():
    page = request.args.get('page', 1, type=int)
    items_per_page = 15

    estate_data = load_estate_data()

    city, status, min_price, max_price, property_type = get_form_data()

    posts = Post.query.order_by(Post.timestamp.desc()).all()
    posts_data = []

    if posts:
        posts_data = [{'Cover Image': eval(post.file_urls), 'Title': post.title, 'Price': post.rent,
                       'Address': post.location, 'Phone Number': post.phone, 'Whatsapp': post.whatsapp,
                       'Description': post.description, 'Beds': post.bedrooms, 'Baths': post.bathrooms,
                       'Area': post.area, 'Agent Name': post.author.username, 'Date': post.timestamp} for post in posts]

    json_data = estate_data['featured_data'] + estate_data['lefke_data'] + estate_data['guzelyurt_data'] + estate_data['rent_data'] + estate_data['cyprus_data'] + estate_data['iskele_data'] + \
        estate_data['magusa_data'] + estate_data['konut_data'] + estate_data['sale_data_1'] + \
        estate_data['sale_data_2'] + \
        estate_data['sale_data_3'] + estate_data['sale_data_4'] + posts_data

    featured_data = featuring_data(estate_data["lefke_data"],
                                   estate_data["guzelyurt_data"],
                                   estate_data["featured_data"],
                                   estate_data["rent_data"],
                                   estate_data["iskele_data"],
                                   estate_data["magusa_data"],
                                   estate_data["konut_data"],
                                   estate_data["cyprus_data"])

    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(json_data))
    current_page_data = json_data[start_idx:end_idx]

    total_pages = len(json_data) // items_per_page

    return render_template('properties.html', current_page_data=current_page_data, featured_data=featured_data, page=page, total_pages=total_pages)


@app.route('/to-buy')
def to_buy():
    estate_data = load_estate_data()
    page = request.args.get('page', 1, type=int)
    for_sale = []
    items_per_page = 12
    
    json_data = estate_data['featured_data'] + estate_data['lefke_data'] + estate_data['guzelyurt_data'] + estate_data['rent_data'] + estate_data['cyprus_data'] + estate_data['iskele_data'] + \
        estate_data['magusa_data'] + estate_data['konut_data'] + estate_data['sale_data_1'] + \
        estate_data['sale_data_2'] + \
        estate_data['sale_data_3'] + estate_data['sale_data_4'] 

    for item in json_data:
        if item['Status'] == "For Sale":
            for_sale.append(item)
        
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(for_sale))
    current_page_data = for_sale[start_idx:end_idx]

    return render_template('to_buy.html', current_page_data=current_page_data, page=page,
                           total_pages=len(for_sale)//items_per_page)

@app.route('/to-rent')
def to_rent():
    estate_data = load_estate_data()
    page = request.args.get('page', 1, type=int)
    items_per_page = 10
    for_rent = []
    json_data = estate_data['featured_data'] + estate_data['lefke_data'] + estate_data['guzelyurt_data'] + estate_data['rent_data'] + estate_data['cyprus_data'] + estate_data['iskele_data'] + \
        estate_data['magusa_data'] + estate_data['konut_data'] + estate_data['sale_data_1'] + \
        estate_data['sale_data_2'] + \
        estate_data['sale_data_3'] + estate_data['sale_data_4']

    for item in json_data:
        if item['Status'] == 'To Rent':
            for_rent.append(item)

    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(for_rent))
    current_page_data = for_rent[start_idx:end_idx]

    return render_template('to_rent.html', current_page_data=current_page_data, page=page, total_pages=len(for_rent)//items_per_page)


@app.route('/feature/<feature_name>')
def feature_detail(feature_name):
    
    estate_data = load_estate_data()
    
    json_data = estate_data['featured_data'] + estate_data['lefke_data'] + estate_data['guzelyurt_data'] + estate_data['rent_data'] + estate_data['cyprus_data'] + estate_data['iskele_data'] + \
        estate_data['magusa_data'] + estate_data['konut_data'] + estate_data['sale_data_1'] + \
        estate_data['sale_data_2'] + \
        estate_data['sale_data_3'] + estate_data['sale_data_4']

    if feature_name == 'bus-stop':
        feature = 'Bus Stop'
        filtered_data = []
        
        for property_listing in json_data:
            for feature_dict in property_listing.get("Outside Features", []):
                for key, value in feature_dict.items():
                    if feature in key:
                        filtered_data.append(property_listing)
                        
        return render_template('features.html', title=feature_name, filtered_data=filtered_data, )

    elif feature_name == 'swimming-pool':
        feature = 'Pool'
        filtered_data = [item for item in json_data if feature in item.get(
            "Pool", [])]
        return render_template('features.html', title=feature_name, filtered_data=filtered_data, )

    elif feature_name == 'private-security':
        feature = 'Security Cam'
        filtered_data = [item for item in json_data if feature in item.get(
            "Outside Features", [])]
        return render_template('features.html', title=feature_name, filtered_data=filtered_data, )

    elif feature_name == 'medical-center':
        feature = 'Hastanesi'
        filtered_data = []
        
        for property_listing in json_data:
            for feature_dict in property_listing.get("Outside Features", []):
                for key, value in feature_dict.items():
                    if feature in key:
                        filtered_data.append(property_listing)

        return render_template('features.html', title=feature_name, filtered_data=filtered_data)

    elif feature_name == 'building-age':
        feature = 'New Building'
        filtered_data = [item for item in json_data if feature in item.get(
            "Building Age", [])]
        return render_template('features.html', title=feature_name, filtered_data=filtered_data, )

    elif feature_name == 'furnished':
        feature = 'Furnished'
        filtered_data = [item for item in json_data if feature in item.get(
            'Furnishing Type', [])]
        return render_template('features.html', title=feature_name, filtered_data=filtered_data, )

    elif feature_name == 'park':
        feature = 'Closed Park'
        filtered_data = [item for item in json_data if feature in item.get(
            "Outside Features", [])]
        return render_template('features.html', title=feature_name, filtered_data=filtered_data, )
   
    elif feature_name == 'with-garden':
        feature = 'Yes'
        filtered_data = [item for item in json_data if feature in item.get(
            "Garden", [])]
        return render_template('features.html', title=feature_name, filtered_data=filtered_data, )

    else:
        return "Invalid feature name"


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/account')
@login_required
def account() -> str:
    '''Render the account page'''
    
    return render_template('account.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout() -> str:
    '''Logout the current user'''
    logout_user()
    return redirect(url_for('home_page'))
