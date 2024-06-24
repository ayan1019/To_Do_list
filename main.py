from flask import Flask, render_template,redirect,url_for,request,flash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField,DateField,SelectField,IntegerField
from flask_ckeditor import CKEditorField,CKEditor
from wtforms.validators import DataRequired, Email, Length, ValidationError, Regexp
import datetime as dt
import smtplib,os,secrets
import schedule
import time
from dotenv import load_dotenv

load_dotenv("/Users/ayan/PycharmProjects/To_Do_list/environ.env")

load_dotenv()
my_email=os.getenv("MyEmail")
password=os.getenv("MyPassword")
to_addr=os.getenv("MyEmail")
smtplib.SMTP("smtp.gmail.com", port=587)


choices=['Business','Personal','Household']
# print(dt.datetime.now().date())

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
ckeditor = CKEditor(app)


############# Flask Login

login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'home'
login_manager.login_message = "Please login/Register to view this page"

############ Flask login manager Load

@login_manager.user_loader
def load_user(user_id):
    with app.app_context():
        return db.session.get(UserDetails, int(user_id))



############# Database Creation

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


############# Form Construction


def date_check(form, field):
        """custom validator to check date in wtform entry is not before today's date, raise Validation Error if it is"""
        print(field)
        if field.data < dt.datetime.now().date():
            raise ValidationError("Due Date can't be in the past!")

class RegisterForm(FlaskForm):
    email=StringField("Email",validators=[DataRequired(),Email(message='Enter a valid email')])
    password=PasswordField("Password",validators=[DataRequired(),Length(min=8)])
    name=StringField("Name",validators=[DataRequired()])
    submit=SubmitField("SIGN ME UP")

class LoginForm(FlaskForm):
    email=StringField("Email",validators=[DataRequired(),Email(message='Enter a valid email')])
    password=PasswordField("Password",validators=[DataRequired()])
    submit=SubmitField("Let Me In")

class AddNewCategory(FlaskForm):
    new_category=StringField("Add New Category",validators=[DataRequired()])
    submit = SubmitField("Add")

class AddTaskForm(FlaskForm):
    todo_task_name=StringField("Task Name",validators=[DataRequired()])
    global choices
    print(choices)
    category = SelectField("Category", choices=choices, coerce=str, validators=[DataRequired()])
    add_category_button = SubmitField("Add New Category")
    due_date=DateField("Due Date",format='%Y-%m-%d',validators=[DataRequired(),date_check])
    add_task_button = SubmitField("Add task")


class AddSubTaskForm(FlaskForm):
    subtask_name = StringField("Task Name", validators=[DataRequired()])
    add_task_button = SubmitField("Add Task")

class ContactForm(FlaskForm):
    name=StringField("Name",validators=[DataRequired()])
    email=StringField("Enter your email",validators=[DataRequired(), Email(message="Please enter a valid email with '@' and '.'"),Length(min=8)])
    phone_number=StringField('Phone Number',validators=[DataRequired(),Length(min=10, max=14),Regexp(regex='^[+-]?[0-9]+$')])
    message=CKEditorField('Message',validators=[DataRequired()])
    submit=SubmitField("SEND")

############# Database table construction

class UserDetails(UserMixin,db.Model):
    __tablename__="user_details"
    id = db.Column(db.Integer, primary_key=True)
    email=db.Column(db.String(250), nullable=False,unique=True)
    password=db.Column(db.String(250), nullable=False)
    name=db.Column(db.String(250), nullable=False)
    tasks=db.relationship("Tasks",back_populates="user",lazy='subquery')
    subtasks = db.relationship("Subtasks", back_populates="user", lazy='subquery')


class Tasks(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    #### Adding Foreign Key and referring back to userdetails table
    user_id=db.Column(db.Integer,db.ForeignKey("user_details.id"))
### if we use backref in parent table then we can comment out the author declaration below.
    user = relationship("UserDetails", back_populates="tasks",lazy='subquery')
    todo_task = db.Column(db.String(250),nullable=False)
    category = db.Column(db.String(250), nullable=False)
    date_added=db.Column(db.String(250), nullable=False)
    due_date = db.Column(db.String(250), nullable=False)
    status= db.Column(db.String(250), nullable=False)
    sub_tasks=db.relationship("Subtasks", back_populates="which_todo_task", lazy='subquery')

class Subtasks(db.Model):
    __tablename__="sub-tasks"
    id=db.Column(db.Integer,primary_key=True)
    subtask_name=db.Column(db.String(250),nullable=False)
    subtask_status=db.Column(db.String(250), nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey("user_details.id"))
    todo_task_id=db.Column(db.Integer,db.ForeignKey("tasks.id"))
    user=relationship("UserDetails",back_populates="subtasks",lazy="subquery")
    which_todo_task=relationship("Tasks",back_populates="sub_tasks",lazy="subquery")
# ######### Line below only required once, when creating DB.
with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/task",methods=['GET','POST'])
def add_task():
    form=AddTaskForm()
    if form.add_task_button.data and form.validate_on_submit():
        # Handle "Add task" button submission
        todo_task = form.todo_task_name.data
        category = form.category.data
        due_date = form.due_date.data
        print(todo_task, category, due_date)
        if form.validate_on_submit():
            try:
                update_task = Tasks.query.filter_by(todo_task=todo_task.title(),user_id=current_user.id,due_date=due_date,category=category).first()
                if update_task==None:

                    new_task = Tasks(
                        user_id=current_user.id,
                        todo_task=todo_task.title(),
                        category=category.title(),
                        date_added=dt.datetime.now().date(),
                        due_date=due_date,
                        status="Active"
                    )
                    db.session.add(new_task)
                    db.session.commit()
                    flash("Task has been successfully added")
                    # print("task has been added")
                    return redirect(url_for("get_all_activities"))
                else:
                    if update_task.status=="Active":
                        flash("Task with the same name is active")
                        return redirect(url_for("add_task",form=form))
                    else:
                        new_task = Tasks(
                            user_id=current_user.id,
                            todo_task=todo_task.title(),
                            category=category.title(),
                            date_added=dt.datetime.now().date(),
                            due_date=due_date,
                            status="Active"
                        )
                        db.session.add(new_task)
                        db.session.commit()
                        flash("Task has been successfully added")
                        # print("task has been added")
                        return redirect(url_for("get_all_activities"))
            except AttributeError:
                flash("Please register/login!")
                return redirect(url_for("home"))


    if form.add_category_button.data:
        # Handle "Add New Category" button submission
        return redirect(url_for('add_new_category'))
    return render_template("add_task.html",form=form)



@app.route("/new_category",methods=['GET','POST'])
@login_required
def add_new_category():
    form1 = AddNewCategory()
    if form1.validate_on_submit():
        global choices
        new_category_name = form1.new_category.data
        choices.append(new_category_name)
        print(choices)
        form2 = AddTaskForm()
        flash("Category has been added")
        return redirect(url_for("add_task", form=form2))
    return render_template("add_new_category.html", form=form1)


@app.route("/get_all_activities",methods=['GET','POST'])
@login_required

def get_all_activities():
    active_tasks=[]
    completed_tasks=[]
    todays_date = str(dt.datetime.now().date())
    with app.app_context():
        all_activities_of_current_user=Tasks.query.filter_by(user_id=current_user.id).all()
        print(all_activities_of_current_user)
        for i in all_activities_of_current_user:
            print(i.todo_task,i.category,i.due_date,i.status)
            if i.status=="Active":
                active_tasks.append(i)
            else:
                completed_tasks.append(i)

    return render_template("get_all_activities.html",all_task_list=all_activities_of_current_user,active_tasks=active_tasks,completed_tasks=completed_tasks,date=todays_date)

@app.route("/show_individual_task",methods=['GET','POST'])
@login_required
def show_individual_task():
    task_id=request.args.get("task_id")
    # user_id=request.args.get("user_id")
    print(task_id)
    with app.app_context():
        task=db.session.execute(db.select(Tasks).filter_by(id=task_id,user_id=current_user.id)).scalar_one()
        subtasks=Subtasks.query.filter_by(todo_task_id=task_id,user_id=current_user.id).all()
        print(task.id,task.todo_task,task.category,task.due_date,task.status)
        for i in subtasks:
            print(i.subtask_name,i.subtask_status)
        # session.query(db.users).filter_by(name='Joe', surname='Dodson')
    return render_template("show_task.html",task=task,subtasks=subtasks)

@app.route("/update_maintask")
@login_required
def update_maintask():
    # print("ggggggggggggggggggggggggggggggggggggggg")
    active_subtask_count=0
    completed_task_count=0
    task_id=request.args.get("task_id")
    with app.app_context():
        task = db.session.execute(db.select(Tasks).filter_by(id=task_id, user_id=current_user.id)).scalar_one()
        subtasks = Subtasks.query.filter_by(todo_task_id=task_id, user_id=current_user.id).all()
        print(subtasks)
        # print("lengthhhhhhhhhh",len(subtasks))
        if len(subtasks)==0:
            task.status="Completed"
            flash("Status has been updated")
        else:
            for i in subtasks:
                if i.subtask_status=="Active":
                    active_subtask_count+=1
                else:
                    completed_task_count+=1
            if active_subtask_count>1:
                flash("One or more subtasks are active.Please mark the subtasks complete.")
            else:
                task.status="Completed"
                flash("Status has been updated")

        db.session.commit()
    return redirect(url_for('show_individual_task',task_id=task_id,user_id=current_user.id))



@app.route("/delete_task")
@login_required
def delete_task():
    task_id=request.args.get("task_id")
    user_id=request.args.get("user_id")
    print(task_id,user_id)
    with app.app_context():
        task_to_delete = db.session.execute(db.select(Tasks).filter_by(id=task_id,user_id=user_id)).scalar_one()
        db.session.delete(task_to_delete)
        db.session.commit()
    # print("task has been deleted")
    flash("Task has been deleted")
    return redirect(url_for('get_all_activities'))

######################### All Subtask related functions


@app.route("/update_subtask")
@login_required
def update_subtask():

    subtask_id=request.args.get("subtask_id")
    task_id=request.args.get("task_id")
    with app.app_context():
        subtask = db.session.execute(db.select(Subtasks).filter_by(id=subtask_id)).scalar_one()
        subtask.subtask_status="Completed"
        flash("Status has been Updated")
        db.session.commit()
    return redirect(url_for('show_individual_task',task_id=task_id,user_id=current_user.id))




@app.route("/delete_sub_task")
@login_required
def delete_subtask():
    subtask_id=request.args.get("subtask_id")
    task_id=request.args.get("task_id")

    print(subtask_id)
    with app.app_context():
        subtask_to_delete = db.session.execute(db.select(Subtasks).filter_by(id=subtask_id)).scalar_one()
        db.session.delete(subtask_to_delete)
        db.session.commit()
    # print("task has been deleted")
    flash("Subtask has been deleted")
    return redirect(url_for('show_individual_task',task_id=task_id,user_id=current_user.id))



@app.route("/add_subtask",methods=['GET','POST'])
@login_required
def add_sub_task():
    task_id=request.args.get("task_id")
    form = AddSubTaskForm()
    if form.validate_on_submit():
        subtask_name = form.subtask_name.data

        print(subtask_name)
        new_subtask = Subtasks(
            user_id=current_user.id,
            subtask_name=subtask_name.title(),
            subtask_status="Active",
            todo_task_id=task_id
        )
        db.session.add(new_subtask)
        db.session.commit()
        # print("Subtask has been added")
        flash("Subtask has been added")
        return redirect(url_for("show_individual_task",task_id=task_id))

    return render_template("add_subtask.html", form=form)





##########################    user related functions

@app.route("/signin",methods=['GET','POST'])
def signin():
    form=LoginForm()
    if form.validate_on_submit():
        email=form.email.data
        password=form.password.data
        print("login",email,password)
        with app.app_context():
            existing_user = UserDetails.query.filter_by(email=email).first()
            if existing_user == None:
                flash("User Doesn't exist.Please Register!")
                # print("user Doesn't exist")
                return redirect(url_for("signup"))
            elif check_password_hash(existing_user.password, password):
                login_user(existing_user)
                flash("You are logged in")
                # print("logged in")
                return redirect(url_for("get_all_activities", logged_in_or_not=True))
            else:
                flash("Wrong Details!")
                # print("wrong Details")
    return render_template("signin.html",form=form)

@app.route("/signup",methods=['GET','POST'])
def signup():
    form=RegisterForm()
    if form.validate_on_submit():
        email=form.email.data
        password=form.password.data
        salt_length = 8
        new_password = generate_password_hash(password, method='pbkdf2:sha256:100000', salt_length=salt_length)
        name=form.name.data.title()
        print(email, new_password, password, name)
        with app.app_context():
            check_user = UserDetails.query.filter_by(email=email).first()
            if check_user == None:
                new_user = UserDetails()
                new_user.email = email  ## form.email.data will also work
                new_user.password = new_password
                new_user.name = name
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                flash("You have successfully registered!")
                # print("success")
                login_user(new_user)
                return redirect(url_for("add_task"))
            else:
                flash("User already exists!")
                # print("user exists")
                return redirect(url_for("signin"))

    return render_template("signup.html",form=form)


@app.route('/logout')
@login_required
def signout():
    logout_user()
    flash("You are logged out")
    # print("you have been logged out")
    return redirect(url_for('home'))


@app.route("/contact",methods=['GET','POST'])
def contact():
    form=ContactForm()
    try:
        if form.validate_on_submit():
            email_body = f"Name :- {form.name.data}\nEmail:- {form.email.data}\nPhone Number:-{form.phone_number.data}\nMessage:-\n{form.message.data}\n"
            with smtplib.SMTP_SSL("smtp.gmail.com") as connection:
                connection.login(user=my_email, password=password)
                connection.sendmail(from_addr=my_email, to_addrs=to_addr,
                                    msg=f"Subject:A New Message\n\nHi,\n\n{email_body}\n")
            flash("Thanks for contacting.You will hear soon!")
            return redirect(url_for('home'))
        return render_template("contact.html",form=form)
    except AttributeError:
        current_user.name="blank"
        return render_template("contact.html",form=form)


# @app.route('/check_duedates')
def check_duedates():
    todays_date=dt.datetime.now().date()
    # print(str(todays_date),"todaysssssssssssssssssss")
    with app.app_context():

###### to get all the userid's from UserDetails Table
        # all_users_id = [user.id for user in UserDetails.query.all()]
        id_list_yes=[]
        id_list_no=[]
        no_list=[]
        final_no_list=[]
        all_tasks_date=[(tasks.due_date , tasks.user_id,tasks.todo_task,tasks.status) for tasks in Tasks.query.all()]
        for i in all_tasks_date:
            if i[0] == str(todays_date) and i[3]=="Active":
                id_list_yes.append((i[1],i[2]))
            else:
                id_list_no.append((i[1],i[2]))

        for i in id_list_no:
            if i[0] not in id_list_yes[0]:
                no_list.append(i[0])
        [final_no_list.append(x) for x in no_list if x not in final_no_list]
        for i in id_list_yes:
            user_data=UserDetails.query.filter_by(id=i[0]).first()
            email=user_data.email
            name=user_data.name
            task_name=i[1]
            # print(f"Hi {name}, Your email:-{email}. The {task_name} is due today")
            with smtplib.SMTP_SSL("smtp.gmail.com") as connection:
                connection.login(user=my_email, password=password)
                connection.sendmail(from_addr=my_email, to_addrs=email,
                                    msg=f"Subject:Message from ToDo Pro\n\nHi {name},\n\nThe {task_name} is due today\nToDo Pro")
        for i in final_no_list:
            user_data=UserDetails.query.filter_by(id=i).first()
            name=user_data.name
            email=user_data.email
            # print(f"Hi {name},Your email:- {email}.You dont have any tasks pending today")
            with smtplib.SMTP_SSL("smtp.gmail.com") as connection:
                connection.login(user=my_email, password=password)
                connection.sendmail(from_addr=my_email, to_addrs=email,
                                    msg=f"Subject:Message from ToDo Pro\n\nHi {name},\n\nYou dont have any tasks pending today\nToDo Pro")

    # return "<h1>hello</h1>"

def schedule_task():
    schedule.every().day.at("06:00").do(check_duedates)

# Start the scheduled task in a separate thread
def start_scheduled_task():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':


    schedule_task()

    # Start the scheduled task in a separate thread
    import threading

    thread = threading.Thread(target=start_scheduled_task)
    thread.start()
    app.run(debug=True)
