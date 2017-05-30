# catalog
Udacity - Item Catalog App


## Description
A web application that provides a list of items within a variety of categories and integrates third party user registration and authentication. Authenticated users have the ability to post, edit, and delete their own items


## Requirements
- [Vagrant](https://www.vagrantup.com/)
- [VirtualBox](https://www.virtualbox.org/)
- [Python ~2.7](https://www.python.org/)


## Set Up

For an initial set up please follow these 2 steps:

1. Download or clone the [fullstack-nanodegree-vm repository](https://github.com/udacity/fullstack-nanodegree-vm).

2. Find the *catalog* folder and replace it with the content of this current repository, by either downloading it or cloning it - [Github Link](https://github.com/megfh/Item-Catalog.git).


## Usage

Launch the Vagrant VM from inside the *vagrant* folder with:

`vagrant up`

`vagrant ssh`

Then move inside the catalog folder:

`cd /vagrant/catalog`

Then run the application:

`python application.py`

You will then be able to browse the application at this URL:

`http://localhost:5000/`

It is important you use *localhost* instead of *0.0.0.0* inside the URL address. That will prevent OAuth from failing.


## Credits

This project is connected to Udacity's Full Stack Foundations and Authentication and Authorization courses, drawing from, modifying, and building off of the code presented in the courses.
