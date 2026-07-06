-- Active: 1783331652182@@127.0.0.1@3306@pirovigia
drop DATABASE if exists PiroVigia;
create database if not exists PiroVigia;
use PiroVigia;
create table if NOT exists detecciones (
    id serial primary key,
    latitude numeric(7, 4),
    longitude numeric(7, 4),
    brightness numeric(5, 1),
    scan numeric(3, 1),
    track numeric(3, 1),
    acq_date date,
    acq_time INT,
    satellite varchar(10),
    instrument VARCHAR(20) DEFAULT 'MODIS',
    confidence INT,
    version VARCHAR(10),
    bright_t31 numeric(5, 1),
    frp numeric(6, 1),
    daynight varchar(40),
    pais VARCHAR(50)
);