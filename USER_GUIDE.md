# User Guide
- [User Guide](#user-guide)
  - [Unauthencated User](#unauthencated-user)
    - [Visiting the school](#visiting-the-school)
  - [Administrator](#administrator)
    - [Testing login credentials](#testing-login-credentials)

## Unauthencated User
### Visiting the school
1. Navigate to the [web page](12458.pythonanywhere.com)
2. Select any location to get started on the tour
3. View the facility's description
4. Naviagte around the school by clicking on the exit locations on the right of the screen 

## Administrator
- [Login Page](/login)
  - Login Here
  - Login button can be found on top right of screen (desktop) or in the burger menu (mobile)
- [Main Administation Page](/admin)
  - Similar to the unauthencated user view but you are able to now select a location and edit it
- [View Location (Select a location)](/view_location/<id>)
  - View the location and edit the location here.
  - You can also see and exit from the exits from here.
- [Edit Location](/edit/<location>)
  - Edit the specified location
  - Access by going to the view location page and clicking the edit button below the description
  - In the edit page, you are able to specify the exits between that location and other locations
  - You are also able to update the location's Name, Description, Capacity, Availability and image
- [Manage Exits](/add_link)
  - Add / Remove / View the exits between locations
  - A graphical view is provided here to assist you in linking the locations
  - This page is an alternative way to link locations together. The other method is to use the Edit Location page
- [Manage Locations](/add_location)
  - Use this page to add more locations to the school tour
  - A list of existing locations is provided to assist you in knowing which locations already exists
    - This prevents the administrator from accidentially keying in duplicate locations
- [Manage Admin](/manage_admin)
  - Use this page to manage Administrator accounts
  - You can add and delete administrators accounts here
- [Logout](/logout)
  - Log out of your admin account
  - Accessible by clicking on the red exit button on the top right of the screen (or in the burger menu on mobile)
- Analytics
  - Google Analytics can be used to see web traffic
  - See `/docs/analytics.png` for evidience of feature
  ![analytics.png](/docs/analytics.png)

### Testing login credentials
Username: `admin`\
Password: `admin`