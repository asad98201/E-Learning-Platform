from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, jsonify, send_from_directory, abort
import io
import os
import datetime
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "/path/to/uploads"
SUBMISSION_FOLDER = 'C:/path/to/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'talha2323'  # Replace with your actual root password
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_DB'] = 'ep'  # Replace with your actual database name
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

#Uncomment this section when your database is ready
import mysql.connector
db = mysql.connector.connect(
    host="localhost",
    user="root",          # Replace with your MySQL username
    password="talha2323",          # Replace with your MySQL password
    database="ep"
)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_type = request.form.get("login_type")  # "student", "teacher", or "admin"
        if login_type == "admin":
            # Admin login: check username and password
            username = request.form.get("username")  # Use 'username' for admin login
            password = request.form.get("password")
            def log_attempt(email, login_type, success):
                try:
                    cursor = db.cursor()
                    query = """
                        INSERT INTO Login_Logs (Email, Login_Type, Success, Attempt_Timestamp)
                        VALUES (%s, %s, %s, NOW())
                    """
                    cursor.execute(query, (username, login_type, success))
                    db.commit()
                except Exception as e:
                    print(f"Logging failed: {e}")
                finally:
                    cursor.close()

        if login_type == "admin":
            # Admin credentials hardcoded
            if username.lower() == "admin" and password == "admin":
                flash("Welcome, Admin!", "success")
                return redirect(url_for("admin_dashboard"))
            else:
                flash("Invalid admin credentials.", "error")
        
        else:
            # Determine the table and ID field based on login type
            password = request.form.get("password")
            table = "Student" if login_type == "student" else "Teacher"
            id_field = f"{table}_id"
            
            try:
                # Create a database cursor
                cursor = db.cursor(dictionary=True)
                
                # Query to validate email and password
                email = request.form.get("email")  # Email for student and teacher login
                query = f"SELECT {id_field}, First_name, Password FROM {table} WHERE Email = %s"
                cursor.execute(query, (email,))
                user = cursor.fetchone()
                
                if user and user["Password"] == password:
                    # Store session data
                    session["user_id"] = user[id_field]
                    session["user_type"] = login_type
                    session["first_name"] = user["First_name"]  # Store for personalization
                    
                    # Redirect to respective homepage
                    if login_type == "student":
                        return redirect(url_for("student_homepage"))
                    elif login_type == "teacher":
                        return redirect(url_for("teacher_homepage"))
                else:
                    flash("Invalid email or password. Please try again.", "error")
            
            except Exception as e:
                flash(f"An error occurred: {e}", "error")
            
            finally:
                cursor.close()
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Capture form data
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password")
        address = request.form.get("address")
        phone_number = request.form.get("phone_number")
        date_of_birth = request.form.get("date_of_birth")

        try:
            # Start a transaction
            cursor = db.cursor()
            db.start_transaction()

            # Insert into Student table
            query = """
                INSERT INTO Student (First_name, Last_name, Email, Password, Date_of_Birth)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (first_name, last_name, email, password, date_of_birth))
            student_id = cursor.lastrowid

            # Insert into Student_Phone table
            query_phone = """
                INSERT INTO Student_Phone (Phone_number, Student_id)
                VALUES (%s, %s)
            """
            cursor.execute(query_phone, (phone_number, student_id))

            # Insert into Student_Address table
            query_address = """
                INSERT INTO Student_Address (Address, Student_id)
                VALUES (%s, %s)
            """
            cursor.execute(query_address, (address, student_id))

            # Commit the transaction
            db.commit()
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for("login"))
        except mysql.connector.Error as err:
            # Rollback the transaction in case of error
            db.rollback()
            flash(f"An error occurred during registration: {err}", "error")
        finally:
            cursor.close()

    return render_template("register.html")


@app.route("/student_homepage")
def student_homepage():
    # Ensure the user is logged in and is a student
    if "user_id" not in session or session["user_type"] != "student":
        flash("Please log in to access the student homepage.", "error")
        return redirect(url_for("login"))

    student_id = session["user_id"]  # Get the logged-in student's ID

    cursor = db.cursor(dictionary=True)

    # Query for the latest 8 courses
    cursor.execute("""
        SELECT 
            Course.Course_id, 
            Course.Course_name AS title, 
            Module.Module_name AS module, 
            CONCAT(Teacher.First_name, ' ', Teacher.Last_name) AS teacher_name
        FROM Course
        JOIN Teacher ON Course.Teacher_id = Teacher.Teacher_id
        LEFT JOIN Module ON Module.Course_id = Course.Course_id
        GROUP BY Course.Course_id
        ORDER BY Course.Course_id DESC
        LIMIT 8
    """)
    new_courses = cursor.fetchall()

    # Query for activities due this week for the logged-in student
    cursor.execute("""
        SELECT 
            Activity.Activity_id,
            Activity.Activity_name AS title, 
            Activity.Due_date, 
            Activity.Description
        FROM Activity
        JOIN Enrollment ON Activity.Course_id = Enrollment.Course_id
        WHERE Enrollment.Student_id = %s 
          AND WEEK(Activity.Due_date) = WEEK(NOW())
        ORDER BY Activity.Due_date ASC
    """, (student_id,))
    activities = cursor.fetchall()

    cursor.close()

    return render_template("student_homepage.html", new_courses=new_courses, activities=activities)

@app.route("/all_courses", methods=["GET", "POST"])
def all_courses():
    # Get search query and filter type from request
    search_query = request.args.get("search", "").strip()
    filter_type = request.args.get("filter", "").strip()

    cursor = db.cursor(dictionary=True)

    # Base query for all courses
    base_query = """
        SELECT 
            Course.Course_id AS id, 
            Course.Course_name AS title, 
            Module.Module_name AS module, 
            CONCAT(Teacher.First_name, ' ', Teacher.Last_name) AS teacher_name
        FROM Course
        LEFT JOIN Teacher ON Course.Teacher_id = Teacher.Teacher_id
        LEFT JOIN Module ON Module.Course_id = Course.Course_id
    """

    # Apply search filter if provided
    if search_query:
        base_query += " WHERE Course.Course_name LIKE %s"
        query_params = [f"%{search_query}%"]
    else:
        query_params = []

    # Apply sorting based on filter type
    if filter_type == "alphabetical":
        base_query += " ORDER BY Course.Course_name ASC"
    elif filter_type == "popularity":
        # Join with Enrollment to count enrollments for popularity
        base_query = """
            SELECT 
                Course.Course_id AS id, 
                Course.Course_name AS title, 
                Module.Module_name AS module, 
                CONCAT(Teacher.First_name, ' ', Teacher.Last_name) AS teacher_name, 
                COUNT(Enrollment.Course_id) AS popularity
            FROM Course
            LEFT JOIN Teacher ON Course.Teacher_id = Teacher.Teacher_id
            LEFT JOIN Module ON Module.Course_id = Course.Course_id
            LEFT JOIN Enrollment ON Enrollment.Course_id = Course.Course_id
            GROUP BY Course.Course_id
            ORDER BY popularity DESC
        """
    elif filter_type == "duration":
        base_query += " ORDER BY Course.Duration ASC"

    try:
        # Execute query
        cursor.execute(base_query, query_params)
        courses = cursor.fetchall()
    except Exception as e:
        flash(f"An error occurred while fetching courses: {e}", "error")
        courses = []
    finally:
        cursor.close()

    # Render the page with retrieved courses
    return render_template("all_courses.html", courses=courses, search_query=search_query)

@app.route('/enrolled_courses')
def enrolled_courses():
    if 'user_id' not in session:
        return redirect('/login')  # Redirect to login if not authenticated

    student_id = session['user_id']  # Fetch the logged-in student ID
    cursor = db.cursor(dictionary=True)
    
    query = """
        SELECT 
            c.Course_id AS id,
            c.Course_name AS title,
            t.First_name AS teacher_name,
            c.Duration AS duration
        FROM Course c
        JOIN Enrollment e ON c.Course_id = e.Course_id
        JOIN Teacher t ON c.Teacher_id = t.Teacher_id
        WHERE e.Student_id = %s;
    """
    cursor.execute(query, (student_id,))
    enrolled_courses = cursor.fetchall()

    return render_template('enrolled_courses.html', enrolled_courses=enrolled_courses)

@app.route("/course/<int:course_id>")
def course_details(course_id):
    cursor = db.cursor(dictionary=True)

    # Fetch course details
    course_query = """
    SELECT 
        c.Course_id AS course_id, -- Include course_id
        c.Course_name AS course_name,
        c.Description AS description,
        c.Duration AS duration,
        c.Pre_Requisite,  -- Fetch prerequisite
        t.First_name AS teacher_name
    FROM Course c
    JOIN Teacher t ON c.Teacher_id = t.Teacher_id
    WHERE c.Course_id = %s;
    """
    cursor.execute(course_query, (course_id,))
    course = cursor.fetchone()

    if not course:
        return "Course not found", 404

    # Fetch enrolled activities
    activities_query = """
    SELECT 
        Activity_id AS activity_id,  -- Add this line
        Activity_name AS title,
        Due_date AS due_date,
        Description
    FROM Activity
    WHERE Course_id = %s;
    """
    cursor.execute(activities_query, (course_id,))
    activities = cursor.fetchall()

    # Fetch module resources
    resources_query = """
    SELECT 
        Resource_id AS id,  -- Make sure you fetch the resource id
        Resource AS resource_name
    FROM Module_Resource mr
    JOIN Module m ON mr.Module_id = m.Module_id
    WHERE m.Course_id = %s;
    """
    cursor.execute(resources_query, (course_id,))
    resources = cursor.fetchall()


    # Fetch modules for the course
    modules_query = """
        SELECT 
            Module_name
        FROM Module
        WHERE Course_id = %s;
    """
    cursor.execute(modules_query, (course_id,))
    modules = cursor.fetchall()

    # Check if the student is enrolled in this course
    student_id = session.get("user_id")  # Fetching student ID from the session
    enrollment_check_query = """
        SELECT * FROM Enrollment WHERE Student_id = %s AND Course_id = %s;
    """
    cursor.execute(enrollment_check_query, (student_id, course_id))
    is_enrolled = bool(cursor.fetchone())

    # Get student count
    student_count_query = """
        SELECT COUNT(*) AS student_count FROM Enrollment WHERE Course_id = %s;
    """
    cursor.execute(student_count_query, (course_id,))
    student_count = cursor.fetchone()["student_count"]

    return render_template("course.html", course=course, activities=activities, resources=resources, modules=modules, is_enrolled=is_enrolled, teacher={"teacher_name": course["teacher_name"]}, student_count=student_count)

@app.route("/download/<int:resource_id>")
def download_resource(resource_id):
    cursor = db.cursor(dictionary=True)

    # Fetch resource details
    resource_query = """
        SELECT Resource AS resource_name 
        FROM Module_Resource 
        WHERE Resource_id = %s;
    """
    cursor.execute(resource_query, (resource_id,))
    resource = cursor.fetchone()

    if not resource:
        return "Resource not found", 404

    file_name = resource["resource_name"]
    try:
        return send_from_directory(UPLOAD_FOLDER, file_name, as_attachment=True)
    except FileNotFoundError:
        return "File not found on server", 404

@app.route("/enroll_course/<int:course_id>", methods=["POST"])
def enroll_course(course_id):
    student_id = session.get("user_id")
    if not student_id:
        return redirect("/login")

    cursor = db.cursor()
    query = "INSERT INTO Enrollment (Student_id, Course_id) VALUES (%s, %s)"
    cursor.execute(query, (student_id, course_id))
    db.commit()
    return redirect(f"/course/{course_id}")

@app.route("/unenroll_course/<int:course_id>", methods=["POST"])
def unenroll_course(course_id):
    student_id = session.get("user_id")
    if not student_id:
        return redirect("/login")

    cursor = db.cursor()
    query = "DELETE FROM Enrollment WHERE Student_id = %s AND Course_id = %s"
    cursor.execute(query, (student_id, course_id))
    db.commit()
    return redirect(f"/course/{course_id}")


@app.route("/activities")
def activities():
    # Fetch student ID from the session (ensure the user is logged in)
    student_id = session.get("user_id")
    if not student_id:
        return redirect("/login")  # Redirect to login page if the student is not logged in

    # Create a database cursor
    cursor = db.cursor(dictionary=True)

    # Query to fetch courses and activities the student is enrolled in
    query = """
        SELECT 
            c.Course_name AS course_name, 
            a.Activity_id AS activity_id,
            a.Activity_name AS activity_title, 
            a.Due_date AS due_date, 
            a.Description AS description
        FROM Enrollment e
        JOIN Course c ON e.Course_id = c.Course_id
        JOIN Activity a ON c.Course_id = a.Course_id
        WHERE e.Student_id = %s
        ORDER BY c.Course_name, a.Due_date;
    """
    cursor.execute(query, (student_id,))
    results = cursor.fetchall()

    # Transform the results into a grouped format: {course_name: [activities]}
    courses_activities = {}
    for row in results:
        course_name = row["course_name"]
        activity = {
            "id": row["activity_id"],  # Store activity ID for linking
            "title": row["activity_title"],
            "due_date": row["due_date"],
            "description": row["description"]
        }
        if course_name not in courses_activities:
            courses_activities[course_name] = []
        courses_activities[course_name].append(activity)

    # Final format for rendering
    courses_activities = [{"course_name": k, "activities": v} for k, v in courses_activities.items()]

    return render_template("activities.html", courses_activities=courses_activities)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route("/activity/<int:activity_id>", methods=["GET", "POST"])
def activity_details(activity_id):
    cursor = db.cursor(dictionary=True)

    # Fetch activity details
    activity_query = """
        SELECT 
            Activity_id AS activity_id,
            Activity_name AS title,
            Due_date AS due_date,
            Description AS description
        FROM Activity
        WHERE Activity_id = %s;
    """
    cursor.execute(activity_query, (activity_id,))
    activity = cursor.fetchone()

    if not activity:
        return "Activity not found", 404

    if request.method == "POST":
        # Handle file upload
        if 'file' not in request.files:
            return "No file part in the request", 400
        file = request.files['file']
        if file.filename == '':
            return "No file selected", 400

        if file:
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            return "File uploaded successfully", 200

    return render_template("activity.html", activity=activity)

@app.route('/feedback')
def feedback():
    # Fetch student_id from session (assuming logged-in user)
    student_id = session.get('user_id')

    # Query to fetch enrolled courses and teacher info for feedback
    cursor = db.cursor(dictionary=True)
    query = """
        SELECT 
            c.Course_id, 
            c.Course_name, 
            m.Module_name, 
            t.First_name AS teacher_first_name, 
            t.Last_name AS teacher_last_name, 
            t.Teacher_id
        FROM Enrollment e
        JOIN Course c ON e.Course_id = c.Course_id
        JOIN Teacher t ON c.Teacher_id = t.Teacher_id
        JOIN Module m ON c.Course_id = m.Course_id
        WHERE e.Student_id = %s;
    """
    cursor.execute(query, (student_id,))
    enrolled_courses = cursor.fetchall()

    return render_template('feedback.html', enrolled_courses=enrolled_courses)



@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    data = request.get_json()
    course_id = data['course_id']
    teacher_id = data['teacher_id']
    feedback_text = data['feedback_text']
    student_id = session.get('user_id')

    if not student_id:
        return jsonify({"message": "No student_id found"}), 400  # Bad request

    # Get current date
    date_submitted = datetime.now().strftime('%Y-%m-%d')

    # Insert feedback into the database
    try:
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO Feedback (Feedback_text, Submit_date, Student_id, Teacher_id, Course_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (feedback_text, date_submitted, student_id, teacher_id, course_id)
        )
        db.commit()
        return jsonify({"message": "Feedback submitted successfully!"}), 200
    except Exception as e:
        print(f"Error submitting feedback: {e}")
        return jsonify({"message": "Error submitting feedback. Please try again."}), 500  # Internal server error

@app.route("/account", methods=["GET"])
def account():
    try:
        # Fetch student details
        cursor = db.cursor(dictionary=True)
        query = """
            SELECT 
                Student.Student_id, 
                Student.First_name, 
                Student.Last_name, 
                Student.Email, 
                Student.Date_of_Birth, 
                Student_Phone.Phone_number, 
                Student_Address.Address
            FROM Student
            LEFT JOIN Student_Phone ON Student.Student_id = Student_Phone.Student_id
            LEFT JOIN Student_Address ON Student.Student_id = Student_Address.Student_id
            WHERE Student.Student_id = %s
        """
        cursor.execute(query, (session["user_id"],))
        student = cursor.fetchone()

        if not student:
            flash("Account details not found.", "error")
            return redirect(url_for("student_homepage"))

        return render_template("account.html", student=student)

    except Exception as e:
        flash(f"An error occurred: {e}", "error")
        return redirect(url_for("student_homepage"))
    finally:
        cursor.close()

@app.route("/t_account", methods=["GET"])
def t_account():
    try:
        # Fetch teacher details
        cursor = db.cursor(dictionary=True)
        query = """
            SELECT 
                Teacher.Teacher_id, 
                Teacher.First_name, 
                Teacher.Last_name, 
                Teacher.Email,
                Teacher_Phone.Phone_number, 
                Teacher_Address.Address
            FROM Teacher
            LEFT JOIN Teacher_Phone ON Teacher.Teacher_id = Teacher_Phone.Teacher_id
            LEFT JOIN Teacher_Address ON Teacher.Teacher_id = Teacher_Address.Teacher_id
            WHERE Teacher.Teacher_id = %s
        """
        cursor.execute(query, (session["user_id"],))
        teacher = cursor.fetchone()

        if not teacher:
            flash("Account details not found.", "error")
            return redirect(url_for("teacher_homepage"))

        return render_template("t_account.html", teacher=teacher)

    except Exception as e:
        flash(f"An error occurred: {e}", "error")
        return redirect(url_for("teacher_homepage"))
    finally:
        cursor.close()

@app.route("/update_account", methods=["POST"])
def update_account():
    data = request.json
    field = data.get("field")
    value = data.get("value")
    password = data.get("password")

    try:
        cursor = db.cursor(dictionary=True)
        
        # Check user type and table
        user_table = "Student" if session.get("role") == "student" else "Teacher"
        user_id_field = f"{user_table}_id"

        # Validate password
        cursor.execute(
            f"SELECT * FROM {user_table} WHERE {user_id_field}=%s AND Password=%s",
            (session["user_id"], password),
        )
        user = cursor.fetchone()

        if not user:
            return jsonify({"success": False, "message": "Invalid password."})

        # Update field
        query = f"UPDATE {user_table} SET {field}=%s WHERE {user_id_field}=%s"
        cursor.execute(query, (value, session["user_id"]))
        db.commit()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    finally:
        cursor.close()

@app.route('/teacher_homepage', methods=['GET'])
def teacher_homepage():
    if 'user_id' not in session:
        return redirect('/login')  # Redirect to login if not logged in

    teacher_id = session['user_id']
    cursor = db.cursor(dictionary=True)

    # Fetch courses taught by the teacher
    query = """
        SELECT 
            Course_id AS course_id, 
            Course_name AS course_name, 
            Duration AS duration, 
            Description 
        FROM Course 
        WHERE Teacher_id = %s
    """
    cursor.execute(query, (teacher_id,))
    courses = cursor.fetchall()

    return render_template('teacher_homepage.html', courses=courses)

@app.route("/t_course/<int:course_id>")
def t_course_details(course_id):
    cursor = db.cursor(dictionary=True)

    # Fetch course details
    course_query = """
    SELECT 
        c.Course_id AS course_id,
        c.Course_name AS course_name,
        c.Description AS description,
        c.Duration AS duration,
        c.Pre_Requisite,
        t.First_name AS teacher_name
    FROM Course c
    JOIN Teacher t ON c.Teacher_id = t.Teacher_id
    WHERE c.Course_id = %s;
    """
    cursor.execute(course_query, (course_id,))
    course = cursor.fetchone()

    if not course:
        return "Course not found", 404

    # Fetch activities
    activities_query = """
    SELECT 
        Activity_id AS activity_id,
        Activity_name AS title,
        Due_date AS due_date,
        Description
    FROM Activity
    WHERE Course_id = %s;
    """
    cursor.execute(activities_query, (course_id,))
    activities = cursor.fetchall()

    # Fetch modules
    modules_query = """
    SELECT 
        Module_id AS module_id,
        Module_name
    FROM Module
    WHERE Course_id = %s;
    """
    cursor.execute(modules_query, (course_id,))
    modules = cursor.fetchall()

    # Fetch existing module resources
    resources_query = """
    SELECT 
        Resource_id AS id,
        Resource AS resource_name
    FROM Module_Resource mr
    JOIN Module m ON mr.Module_id = m.Module_id
    WHERE m.Course_id = %s;
    """
    cursor.execute(resources_query, (course_id,))
    resources = cursor.fetchall()

    return render_template(
        "t_course.html", 
        course=course, 
        activities=activities,
        modules=modules, 
        resources=resources
    )

@app.route("/upload_resource/<int:course_id>", methods=["POST"])
def upload_resource(course_id):
    if "file" not in request.files or "resource_name" not in request.form:
        return "File or resource name not provided", 400

    file = request.files["file"]
    resource_name = request.form["resource_name"]

    if file.filename == "":
        return "No selected file", 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        # Insert the resource into the database
        cursor = db.cursor()
        module_id_query = """
        SELECT Module_id FROM Module WHERE Course_id = %s LIMIT 1;
        """
        cursor.execute(module_id_query, (course_id,))
        module = cursor.fetchone()

        if not module:
            return "Module not found for this course", 404

        module_id = module["Module_id"]

        insert_resource_query = """
        INSERT INTO Module_Resource (Module_id, Resource, Resource_name)
        VALUES (%s, %s, %s);
        """
        cursor.execute(insert_resource_query, (module_id, filename, resource_name))
        db.commit()

        return redirect(url_for("t_course_details", course_id=course_id))
    else:
        return "Invalid file type", 400
    
@app.route('/admin_dashboard')
def admin_dashboard():
    # List of table names
    tables = [
        "Student", "Student_Phone", "Student_Address", "Teacher", 
        "Teacher_Phone", "Teacher_Address", "Course", "Module", 
        "Module_Resource", "Enrollment", "Activity", "Feedback"
    ]
    return render_template('admin_dashboard.html', tables=tables)

@app.route('/table/<table_name>', methods=['GET'])
def table_view(table_name):
    try:
        # Create a cursor
        cursor = db.cursor(dictionary=True)  # Use dictionary=True to return rows as dictionaries

        # Describe table to get columns
        cursor.execute(f"DESCRIBE {table_name}")
        columns = [row['Field'] for row in cursor.fetchall()]  # Extract column names

        # Fetch all rows from the table
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()  # Fetch all rows as a list of dictionaries

        # Close the cursor
        cursor.close()

        return render_template('table.html', table_name=table_name, columns=columns, rows=rows)
    except Exception as e:
        return f"Error loading table: {e}", 500

@app.route('/update_row/<table_name>', methods=['POST'])
def update_row(table_name):
    data = request.form.to_dict()  # Get form data as dictionary
    row_id = data.pop('id', None)  # Assuming 'id' is the primary key
    if not row_id:
        return jsonify({"success": False, "error": "Missing row ID"}), 400

    # Prepare the SET clause for SQL update
    set_clause = ', '.join([f"{key} = %s" for key in data.keys()])
    query = f"UPDATE {table_name} SET {set_clause} WHERE id = %s"
    values = list(data.values()) + [row_id]

    try:
        # Create a cursor
        cursor = db.cursor()

        # Execute the update query
        cursor.execute(query, values)
        db.commit()  # Commit the changes

        # Close the cursor
        cursor.close()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/insert_row/<table_name>', methods=['POST'])
def insert_row(table_name):
    data = request.form.to_dict()  # Get form data as dictionary
    columns = ', '.join(data.keys())  # Columns for the insert query
    placeholders = ', '.join(['%s'] * len(data))  # Placeholder for values
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    values = [v if v else None for v in data.values()]  # Replace empty fields with None

    try:
        # Create a cursor
        cursor = db.cursor()

        # Execute the insert query
        cursor.execute(query, values)
        db.commit()  # Commit the changes

        # Close the cursor
        cursor.close()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/delete_row/<table_name>/<int:row_id>', methods=['DELETE'])
def delete_row(table_name, row_id):
    query = f"DELETE FROM {table_name} WHERE id = %s"

    try:
        # Create a cursor
        cursor = db.cursor()

        # Execute the delete query
        cursor.execute(query, (row_id,))
        db.commit()  # Commit the changes

        # Close the cursor
        cursor.close()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/logout')
def logout():
    # Clear the user session
    session.clear()
    # Redirect to the login page
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)