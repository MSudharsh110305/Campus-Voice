// Authoritative Enum Definitions

// Full department list matching the backend seed order (id → { code, name })
export const DEPARTMENTS = [
    { id: 1,  code: 'CSE',       name: 'Computer Science & Engineering' },
    { id: 2,  code: 'ECE',       name: 'Electronics & Communication Engineering' },
    { id: 3,  code: 'RAA',       name: 'Robotics and Automation' },
    { id: 4,  code: 'MECH',      name: 'Mechanical Engineering' },
    { id: 5,  code: 'EEE',       name: 'Electrical & Electronics Engineering' },
    { id: 6,  code: 'EIE',       name: 'Electronics & Instrumentation Engineering' },
    { id: 7,  code: 'BIO',       name: 'Biomedical Engineering' },
    { id: 8,  code: 'AERO',      name: 'Aeronautical Engineering' },
    { id: 9,  code: 'CIVIL',     name: 'Civil Engineering' },
    { id: 10, code: 'IT',        name: 'Information Technology' },
    { id: 11, code: 'MBA',       name: 'Management Studies' },
    { id: 12, code: 'AIDS',      name: 'Artificial Intelligence and Data Science' },
    { id: 13, code: 'MTECH_CSE', name: 'M.Tech in Computer Science and Engineering' },
    { id: 14, code: 'ENG',       name: 'English' },
    { id: 15, code: 'PHY',       name: 'Physics' },
    { id: 16, code: 'CHEM',      name: 'Chemistry' },
    { id: 17, code: 'MATH',      name: 'Mathematics' },
];

// Convenience maps
export const DEPARTMENT_BY_ID = Object.fromEntries(DEPARTMENTS.map(d => [d.id, d]));
export const DEPARTMENT_BY_CODE = Object.fromEntries(DEPARTMENTS.map(d => [d.code, d]));

// Legacy alias kept for backward compatibility with existing components
export const DEPARTMENT_LIST = DEPARTMENTS;

export const COMPLAINT_CATEGORIES = {
    1: "Men's Hostel",
    2: "Women's Hostel",
    3: "General",
    4: "Department",
    5: "Disciplinary Committee"
};

export const CATEGORY_LIST = Object.entries(COMPLAINT_CATEGORIES).map(([id, name]) => ({
    id: parseInt(id),
    name
}));

export const STATUSES = [
    "Raised",
    "In Progress",
    "Resolved",
    "Closed",
    "Spam"
];

// Valid status transitions per the backend rules
export const VALID_STATUS_TRANSITIONS = {
    "Raised":      ["In Progress", "Resolved", "Spam"],
    "In Progress": ["Resolved", "Spam"],
    "Resolved":    ["Closed"],
    "Closed":      [],
    "Spam":        ["Closed"],
};

// Statuses that REQUIRE a reason field
export const REASON_REQUIRED_STATUSES = ["Closed", "Spam"];

export const PRIORITIES = [
    "Low",
    "Medium",
    "High",
    "Critical"
];

export const VISIBILITY = {
    PUBLIC: "Public",
    PRIVATE: "Private"
};

export const VOTE_TYPES = {
    UPVOTE: "Upvote",
    DOWNVOTE: "Downvote"
};

export const GENDER = ["Male", "Female", "Other"];

export const STAY_TYPE = ["Hostel", "Day Scholar"];

export const AUTHORITY_TYPES = [
    "Admin",
    "Admin Officer",
    "Men's Hostel Warden",
    "Women's Hostel Warden",
    "Men's Hostel Deputy Warden",
    "Women's Hostel Deputy Warden",
    "Senior Deputy Warden",
    "HOD",
    "Disciplinary Committee"
];

export const AUTHORITY_LEVELS = {
    "Admin": 100,
    "Admin Officer": 50,
    "Disciplinary Committee": 20,
    "Senior Deputy Warden": 15,
    "Men's Hostel Deputy Warden": 10,
    "Women's Hostel Deputy Warden": 10,
    "HOD": 8,
    "Men's Hostel Warden": 5,
    "Women's Hostel Warden": 5,
};

export const NOTICE_CATEGORIES = [
    "Announcement",
    "Policy Change",
    "Event",
    "Maintenance",
    "Emergency",
    "General"
];

export const NOTICE_PRIORITIES = ["Low", "Medium", "High", "Urgent"];
