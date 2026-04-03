from enum import Enum

class UserResponseEnum(Enum):

    USER_CREATE_SUCCESS = "User Created Successfully"
    USER_DELETE_SUCCESS = "User Deleted Successfully"
    USER_UPDATE_SUCCESS = "User Updated Successfully"

    USER_NOT_FOUND = "User not found"
    USERNAME_OR_EMAIL_ALREADY_EXISTS = "Username or email already exists"
    NO_FIELDS_TO_UPDATE = "No fields to update"


