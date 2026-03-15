grammar FinancialRuleLanguage;

// ============================================================
// Parser Rules
// ============================================================

ruleset
    : 'ruleset' IDENTIFIER version? importDecl* globalDecl* ruleDef* EOF
    ;

version
    : 'version' STRING
    ;

importDecl
    : 'import' qualifiedName ('as' IDENTIFIER)?
    ;

globalDecl
    : 'global' type IDENTIFIER
    ;

ruleDef
    : 'rule' IDENTIFIER
      ('priority' INT)?
      ('salience' INT)?
      'when'
        conditionBlock
      'then'
        actionBlock
      ('otherwise' actionBlock)?
    ;

// ------------------------------------------------------------
// Conditions
// ------------------------------------------------------------

conditionBlock
    : singleCondition
    | compoundCondition
    ;

compoundCondition
    : 'all' '(' conditionList ')'
    | 'any' '(' conditionList ')'
    | 'not' '(' conditionBlock ')'
    ;

conditionList
    : conditionBlock (',' conditionBlock)*
    ;

singleCondition
    : factPattern
    | evalExpression
    | existsPattern
    ;

factPattern
    : factType IDENTIFIER? ':' patternConstraint (',' patternConstraint)*
    ;

patternConstraint
    : attribute constraintOp value
    | attribute 'in' listValue
    | attribute 'exists'
    ;

existsPattern
    : 'exists' factPattern
    ;

evalExpression
    : 'eval' '(' STRING ')'
    ;

// ------------------------------------------------------------
// Actions
// ------------------------------------------------------------

actionBlock
    : action (';' action)*
    ;

action
    : insertAction
    | retractAction
    | modifyAction
    | callAction
    | returnAction
    | predictAction
    ;

insertAction
    : 'insert' factType ('(' attributeAssignment (',' attributeAssignment)* ')')?
    ;

retractAction
    : 'retract' IDENTIFIER
    ;

modifyAction
    : 'modify' IDENTIFIER '(' attributeAssignment (',' attributeAssignment)* ')'
    ;

callAction
    : 'call' IDENTIFIER '(' argumentList? ')'
    ;

returnAction
    : 'return' STRING ('with' attributeAssignment (',' attributeAssignment)*)?
    ;

predictAction
    : 'predict' modelRef '(' featureMap ')' ('as' IDENTIFIER)?
    | 'predict' modelRef 'on' IDENTIFIER ('as' IDENTIFIER)?
    ;

modelRef
    : IDENTIFIER ('@' INT)?
    ;

featureMap
    : featureEntry (',' featureEntry)*
    ;

featureEntry
    : IDENTIFIER ':' expression
    ;

// ------------------------------------------------------------
// Shared sub-rules
// ------------------------------------------------------------

qualifiedName
    : IDENTIFIER ('.' IDENTIFIER)*
    ;

factType
    : 'Applicant'
    | 'Policy'
    | 'Claim'
    | 'Payment'
    | 'RiskFactor'
    | 'MLPrediction'
    | 'Decision'
    | IDENTIFIER
    ;

type
    : IDENTIFIER
    ;

attribute
    : IDENTIFIER ('.' IDENTIFIER)*
    ;

constraintOp
    : '==' | '!=' | '>' | '<' | '>=' | '<=' | 'matches' | 'contains'
    ;

value
    : literal
    | attribute
    | calculation
    ;

literal
    : INT
    | FLOAT
    | STRING
    | BOOL
    | NULL
    | listValue
    ;

listValue
    : '[' literal (',' literal)* ']'
    ;

calculation
    : '(' expression ')'
    ;

expression
    : IDENTIFIER
    | literal
    | expression ('+' | '-' | '*' | '/') expression
    | '(' expression ')'
    ;

attributeAssignment
    : IDENTIFIER ':' expression
    ;

argumentList
    : expression (',' expression)*
    ;

// ============================================================
// Lexer Rules
// ============================================================

INT     : [0-9]+ ;
FLOAT   : [0-9]+ '.' [0-9]+ ;
STRING  : '"' (~["\r\n])* '"'
        | '\'' (~['\r\n])* '\''
        ;
BOOL    : 'true' | 'false' ;
NULL    : 'null' ;

IDENTIFIER
    : [a-zA-Z_][a-zA-Z0-9_]*
    ;

WS
    : [ \t\r\n]+ -> skip
    ;

COMMENT
    : '//' ~[\r\n]* -> skip
    ;

BLOCK_COMMENT
    : '/*' .*? '*/' -> skip
    ;
