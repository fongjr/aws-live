from flask import Flask, render_template, request, flash, redirect, url_for, session
from pymysql import connections
import os
import boto3
from config import *
from datetime import datetime
from flask_session import Session

app = Flask(__name__)
# For Flash #
app.secret_key = "hello world" 
# For Session #
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Prepare Database Connection #
db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb
)

# Unused Default Variables #
bucket = custombucket
region = customregion
table = 'employee'
output = {}

# Global Variables #
s3 = boto3.resource('s3')
s3_client = boto3.client('s3')
allow_image = set(['png', 'jpg', 'jpeg', 'gif'])
employee_id = 1001
performance_note_id = 1000

# Functions #
def get_file_extension(filename):
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()

def check_file_extension(filename, allow_extensions):
    if get_file_extension(filename) not in allow_extensions:
        return True
    else:
        return False

# Page Route, Render Web Page #
@app.route("/", methods=['GET', 'POST'])
def home():
    if not session.get("name"):
        return render_template('Login.html')
    else:
        sql_query = "SELECT * FROM employee WHERE NOT EXISTS (SELECT * FROM employee_resigned WHERE employee.emp_id = employee_resigned.emp_id)"
        cursor = db_conn.cursor()
        try:
            cursor.execute(sql_query)
            records = cursor.fetchall()
            totalEmployee = len(records)
            sql_query = "SELECT * FROM performance_note"
            cursor.execute(sql_query)
            records = cursor.fetchall()
            totalPerformanceNote = len(records)
            sql_query = "SELECT * FROM employee_resigned"
            cursor.execute(sql_query)
            records = cursor.fetchall()
            totalResignedEmployee = len(records)
            cursor.close()
        except Exception as e:
            return str(e)
        return render_template('Index.html', totalEmployee = totalEmployee, totalPerformanceNote = totalPerformanceNote, totalResignedEmployee = totalResignedEmployee)

@app.route("/portfolio", methods=['GET', 'POST'])
def portfolio():
    profilePicName = ["fongjiari.jpg", "heekaitek.jpg"]
    profilePicList = []
    # Extract employee cert image #
    for pic in profilePicName:
        public_url = s3_client.generate_presigned_url('get_object', 
                                                        Params = {'Bucket': custombucket, 
                                                                    'Key': pic})
        profilePicList.append(public_url)
    return render_template('Portfolio.html', profilePicList = profilePicList)

# Performance Note Module #
@app.route("/performanceNote", methods=['GET', 'POST'])
def performanceNote():
    sql_query = "SELECT * FROM performance_note WHERE note_visibility='public'"
    cursor = db_conn.cursor()
    try: 
        #  Extract performance note records #
        cursor.execute(sql_query)
        records = list(cursor.fetchall())

        # Put records into a performance note list & Convert rows inside records from tuple to list #
        performanceNotes = []
        for rows in records:
            performanceNotes.append(list(rows))

        cursor.close()
        return render_template('PerformanceNote.html', performanceNotes = performanceNotes)
    except Exception as e:
        return str(e)

@app.route("/addNote", methods=['GET', 'POST'])
def addNote():
    if request.method == "GET":
        # Setting employee list automatically #
        sql_query = "SELECT * FROM employee WHERE NOT EXISTS (SELECT * FROM employee_resigned WHERE employee.emp_id = employee_resigned.emp_id)"
        cursor = db_conn.cursor()
        try: 
            cursor.execute(sql_query)
            records = cursor.fetchall()

            employees = []
            for rows in records:
                employees.append(list(rows))

            # Setting note id automatically #
            sql_query = "SELECT * FROM performance_note"
            cursor.execute(sql_query)
            records = cursor.fetchall()
            note_id = performance_note_id + int(len(records))
            return render_template('AddPerformanceNote.html', employees = employees, noteId = note_id)
        except Exception as e:
            return str(e)
    elif request.method == "POST":
        # Get form fields #
        note_id = request.form['noteId']
        note_target_emp = request.form['empId']
        note_title = request.form['noteTitle']
        note_description = request.form['noteDescription']
        note_report_emp = request.form['noteReporter']
        note_visibility = request.form['noteVisibility']
        
        # Add data to database #
        insert_sql = "INSERT INTO performance_note VALUES (%s, %s, %s, %s, %s, %s)"
        cursor = db_conn.cursor()
        try:
            cursor.execute(insert_sql, (note_id, note_target_emp, note_title, note_description, note_report_emp, note_visibility))
            db_conn.commit()
            flash("Performance Note Added...")
        except Exception as e:
                return str(e)
        finally:
            cursor.close()
        return redirect(url_for('performanceNote'))

@app.route("/modifyNote", methods=['GET', 'POST'])
def modifyNote():
    if request.method == "POST":
        # Get form fields #
        note_id = request.form['noteId']

        # Setting performance notes details back form #
        sql_query = "SELECT * FROM performance_note WHERE note_id = '" + note_id + "'"
        cursor = db_conn.cursor()
        try:
            cursor.execute(sql_query)
            performance_note = list(cursor.fetchone())
        
            # Setting employee list automatically #
            sql_query = "SELECT * FROM employee WHERE NOT EXISTS (SELECT * FROM employee_resigned WHERE employee.emp_id = employee_resigned.emp_id)"
            cursor.execute(sql_query)
            records = list(cursor.fetchall())

            employees = []
            # Convert rows in records from tuple to list #
            for rows in records:
                employees.append(list(rows))

            # If the employee id match with target performance note id add variable selected #
            for rows in employees:
                if rows[0] == performance_note[1]:
                    rows.append("selected")

            cursor.close()
            return render_template('ModifyPerformanceNote.html', performanceNote = performance_note, employees = employees, visibility = performance_note[5])
        except Exception as e:
            return str(e)
    elif request.method == "GET":
        return redirect(url_for('performanceNote'))

@app.route("/modifyNotePerformance", methods=['GET', 'POST'])
def modifyNotePerformance():
    if request.method == "POST":
        # Get form fields #
        note_id = request.form['noteId']
        note_target_emp = request.form['empId']
        note_title = request.form['noteTitle']
        note_description = request.form['noteDescription']
        note_report_emp = request.form['noteReporter']
        note_visibility = request.form['noteVisibility']
        
        # Add data to database #
        update_sql = "UPDATE performance_note SET note_target_emp='" + note_target_emp + "', note_title='"  + note_title + "', note_description='" + note_description + "', note_report_emp='" + note_report_emp + "', note_visibility='" + note_visibility + "' WHERE note_id='" + note_id + "'"
        cursor = db_conn.cursor()
        try:
            # Update data to database #
            cursor.execute(update_sql)
            db_conn.commit()
            flash("Performance Note Modified...")
        except Exception as e:
                return str(e)
        finally:
            cursor.close()
        return redirect(url_for('performanceNote'))
    elif request.method == "GET":
        return redirect(url_for('performanceNote'))

@app.route("/deleteNote", methods=['GET', 'POST'])
def deleteNote():
    if request.method == "POST":
        # Get form fields #
        note_id = request.form['noteId']

        delete_query = "DELETE FROM performance_note WHERE note_id='" + note_id + "'"
        cursor = db_conn.cursor()
        try:
            cursor.execute(delete_query)
            db_conn.commit()
            cursor.close()
            return redirect(url_for('performanceNote'))
        except Exception as e:
            return str(e)
    elif request.method == "GET":
        return redirect(url_for('performanceNote'))

# Employee Module #
@app.route("/employee", methods=['GET', 'POST'])
def employee():
    # Prepare to query database #
    sql_query = "SELECT * FROM employee WHERE NOT EXISTS (SELECT * FROM employee_resigned WHERE employee.emp_id = employee_resigned.emp_id)"
    cursor = db_conn.cursor()
    try: 
        # Extract employee records #
        cursor.execute(sql_query)
        records = list(cursor.fetchall())

        # Put records into an employee list & Convert rows inside records from tuple to list #
        employees = []
        for rows in records:
            employees.append(list(rows))

        cursor.close()
        return render_template('Employee.html', employees = employees)
    except Exception as e:
        return str(e)

@app.route("/addEmp", methods=['GET', 'POST'])
def addEmp():
    if request.method == "GET":
        # Setting employee id automatically #
        sql_query = "SELECT * FROM employee"
        cursor = db_conn.cursor()
        try: 
            cursor.execute(sql_query)
            records = cursor.fetchall()
            emp_id = employee_id + int(len(records))
            cursor.close()
            return render_template('AddEmployee.html', empId = emp_id)
        except Exception as e:
            return str(e)
    elif request.method == "POST":
        # Get form fields #
        emp_id = request.form['empId']
        emp_name = request.form['empName']
        emp_email = request.form['empEmail']
        emp_password = request.form['empPassword']
        emp_training = request.form.getlist('empTraining')
        emp_cert_image = request.files['empCert']
        
        # Form validations #
        sql_query = "SELECT * FROM employee WHERE emp_email='" + emp_email + "'"
        cursor = db_conn.cursor()
        try: 
            cursor.execute(sql_query)
            row = cursor.fetchone()
            cursor.close()
        except Exception as e:
            return str(e)
        if emp_cert_image.filename == "":
            return("Please select a file")
        elif check_file_extension(emp_cert_image.filename, allow_image):
            return("Please select image file only!")
        elif len(emp_training) == 0:
            return("Please select at least one training!")
        elif row != None:
            return("Please select a different email!")
        else:
            # Add data to database #
            insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s, %s)"
            emp_training = ",".join(emp_training)
            image_name_in_s3 = "certifications/emp_id_" + str(emp_id) + "_cert." + get_file_extension(emp_cert_image.filename)
            cursor = db_conn.cursor()
            try:
                cursor.execute(insert_sql, (emp_id, emp_name, emp_email, emp_password, emp_training, image_name_in_s3))
                db_conn.commit()
                try:
                    # Upload image file in S3 #
                    s3.Bucket(custombucket).put_object(Key=image_name_in_s3, Body=emp_cert_image)

                    # Check which region the bucket resides in #
                    bucket_location = s3_client.get_bucket_location(Bucket=custombucket)
                    s3_location = (bucket_location['LocationConstraint'])
                    if s3_location is None:
                        s3_location = ''
                    else:
                        s3_location = '-' + s3_location
                    object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                        s3_location,
                        custombucket,
                        image_name_in_s3)
                    flash("Employee Added...")
                except Exception as e:
                    return str(e)
            except Exception as e:
                    return str(e)
            finally:
                cursor.close()
            return redirect(url_for('employee'))

@app.route("/viewEmp", methods=['GET', 'POST'])
def viewEmp():
    if request.method == "POST":
        # Get form fields #
        emp_id = request.form['empId']

        # Prepare to query database #
        sql_query = "SELECT * FROM employee WHERE emp_id = '" + emp_id + "'"
        cursor = db_conn.cursor()
        try: 
            # Extract employee records #
            cursor.execute(sql_query)
            employee = list(cursor.fetchone())

            # Extract employee cert image #
            public_url = s3_client.generate_presigned_url('get_object', 
                                                                Params = {'Bucket': custombucket, 
                                                                            'Key': employee[5]})

            # Put public_urls into employee list as well and set a variable checked #
            employee.append(public_url)
            employee.append("checked")

            cursor.close()
            return render_template('ViewEmployee.html', employee = employee)
        except Exception as e:
            return str(e)
    elif request.method == "GET":
        return redirect(url_for('employee'))

@app.route("/modifyEmp", methods=['GET', 'POST'])
def modifyEmp():
    if request.method == "POST":
        # Get form fields #
        emp_id = request.form['empId']

        # Prepare to query database #
        sql_query = "SELECT * FROM employee WHERE emp_id = '" + emp_id + "'"
        cursor = db_conn.cursor()
        try: 
            # Extract employee records #
            cursor.execute(sql_query)
            employee = list(cursor.fetchone())

            # Extract employee cert image #
            public_url = s3_client.generate_presigned_url('get_object', 
                                                                Params = {'Bucket': custombucket, 
                                                                            'Key': employee[5]})
            # Put public_urls into employee list as well and set a variable checked #
            employee.append(public_url)
            employee.append("checked")

            cursor.close()
            return render_template('ModifyEmployee.html', employee = employee)
        except Exception as e:
            return str(e)
    elif request.method == "GET":
        return redirect(url_for('employee'))

@app.route("/modifyEmployee", methods=['GET', 'POST'])
def modifyEmployee():
    if request.method == "POST":
        # Get form fields #
        emp_id = request.form['empId']
        emp_name = request.form['empName']
        emp_email = request.form['empEmail']
        emp_password = request.form['empPassword']
        emp_training = request.form.getlist('empTraining')
        emp_cert_image = request.files['empCert']

        # Form validations #
        sql_query = "SELECT * FROM employee WHERE emp_email='" + emp_email + "' AND emp_id!='" + emp_id + "'"
        cursor = db_conn.cursor()
        try: 
            cursor.execute(sql_query)
            row = cursor.fetchone()
            cursor.close()
        except Exception as e:
            return str(e)
        if emp_cert_image.filename != "":
            if check_file_extension(emp_cert_image.filename, allow_image):
                return("Please select image file only!")
        elif len(emp_training) == 0:
            return("Please select at least one training!")
        elif row != None:
            return("Please select a different email!")
        else:
            # Prepare query to database #
            emp_training = ",".join(emp_training)
            if emp_cert_image.filename != "":
                image_name_in_s3 = "certifications/emp_id_" + str(emp_id) + "_cert." + get_file_extension(emp_cert_image.filename)
                update_sql = "UPDATE employee SET emp_name='" + emp_name + "', emp_email ='" + emp_email + "', emp_password ='" + emp_password + "', emp_training ='" + emp_training + "', emp_cert_img ='" + image_name_in_s3 + "' WHERE emp_id ='" + emp_id + "'"
            else:
                update_sql = "UPDATE employee SET emp_name='" + emp_name + "', emp_email ='" + emp_email + "', emp_password ='" + emp_password + "', emp_training ='" + emp_training + "' WHERE emp_id ='" + emp_id + "'"
            cursor = db_conn.cursor()
            try:
                # Update data to database #
                cursor.execute(update_sql)
                db_conn.commit()
                try:
                    # Reupload image file in S3 #
                    if emp_cert_image.filename != "":
                        s3.Object(custombucket, image_name_in_s3).delete()
                        s3.Bucket(custombucket).put_object(Key=image_name_in_s3, Body=emp_cert_image)

                        # Check which region the bucket resides in #
                        bucket_location = s3_client.get_bucket_location(Bucket=custombucket)
                        s3_location = (bucket_location['LocationConstraint'])
                        if s3_location is None:
                            s3_location = ''
                        else:
                            s3_location = '-' + s3_location
                        object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                            s3_location,
                            custombucket,
                            image_name_in_s3)
                    flash("Employee Modified...")
                except Exception as e:
                    return str(e)
            except Exception as e:
                    return str(e)
            finally:
                cursor.close()
            return redirect(url_for('employee'))
    elif request.method == "GET":
        return redirect(url_for('employee'))

@app.route("/deleteEmp", methods=['GET', 'POST'])
def deleteEmp():
    if request.method == "POST":
        # Get form fields #
        emp_id = request.form['empId']

        # Get name based on id #
        sql_query = "SELECT * FROM employee WHERE emp_id = '" + emp_id + "'"
        cursor = db_conn.cursor()
        try: 
            # Extract employee records #
            cursor.execute(sql_query)
            employee = list(cursor.fetchone())
            emp_name = employee[1]

            # Get today date #
            todayDate = datetime.now()
            todayDate = todayDate.strftime("%Y-%m-%d")
            todayDate = str(todayDate)
            print(type(todayDate))
            print(todayDate)

            # Prepare to query database #
            insert_sql = "INSERT INTO employee_resigned VALUES (%s, %s, %s)"

            # Insert employee resigned records #
            cursor.execute(insert_sql, (emp_id, emp_name, todayDate))
            db_conn.commit()
            cursor.close()
            return redirect(url_for('employee'))
        except Exception as e:
            return str(e)
    elif request.method == "GET":
        return redirect(url_for('employee'))

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        sql_query = "SELECT * FROM employee WHERE emp_email='" + email + "' AND NOT EXISTS (SELECT * FROM employee_resigned WHERE employee.emp_id = employee_resigned.emp_id)"
        cursor = db_conn.cursor()
        try: 
            cursor.execute(sql_query)
            row = cursor.fetchone()
            if row != None:
                if row[3] == password:
                    cursor.close()
                    session["name"] = row[1]
                else:
                    flash("Please check your password and try again.", "warning")
            else:
                flash("Please check your login details and try again.", "warning")
        except Exception as e:
            return str(e)
        return redirect(url_for('home'))
    elif request.method == "GET":
        return redirect(url_for('home'))

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    session["name"] = None
    return redirect(url_for('home'))

#
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
