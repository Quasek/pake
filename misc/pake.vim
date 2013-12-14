if exists("b:current_syntax")
  finish
endif

syn keyword pakeDirective       target set append
syn keyword pakeTargetType      application static_library phony
syn keyword pakeArgument        sources link_with depends_on run_before run_after library_dirs include_dirs compiler_flags
syn match pakeSpecialVariable   "__path"
syn match pakeComment           "#.*$"
syn match pakeIdentifier1       "$[^ )]*"
syn match pakeIdentifier2       "${[^ )]*}" contained
syn region pakeString           start='"' end='"' contains=pakeIdentifier2

hi def link pakeDirective        Statement
hi def link pakeTargetType       Type
hi def link pakeArgument         Keyword
hi def link pakeSpecialVariable  Constant
hi def link pakeIdentifier1      Identifier
hi def link pakeIdentifier2      Identifier
hi def link pakeString           Constant
hi def link pakeComment          Comment

let b:current_syntax = "pake"
