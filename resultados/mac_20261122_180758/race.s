	.build_version macos, 27, 2	sdk_version 27, 2
	.section	__TEXT,__literal8,8byte_literals
	.p2align	3, 0x0                          ; -- Begin function main
lCPI0_0:
	.long	0                               ; 0x0
	.long	1                               ; 0x1
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_main
	.p2align	2
_main:                                  ; @main
	.cfi_startproc
; %bb.0:
	sub	sp, sp, #112
	stp	x22, x21, [sp, #64]             ; 16-byte Folded Spill
	stp	x20, x19, [sp, #80]             ; 16-byte Folded Spill
	stp	x29, x30, [sp, #96]             ; 16-byte Folded Spill
	add	x29, sp, #96
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w19, -24
	.cfi_offset w20, -32
	.cfi_offset w21, -40
	.cfi_offset w22, -48
	mov	w20, #33920                     ; =0x8480
	movk	w20, #30, lsl #16
	stur	xzr, [x29, #-40]
	stp	x20, xzr, [sp, #40]
	sub	x8, x29, #40
	add	x21, sp, #40
Lloh0:
	adrp	x19, l___unnamed_1@PAGE
Lloh1:
	add	x19, x19, l___unnamed_1@PAGEOFF
	stp	x21, x8, [sp]
Lloh2:
	adrp	x2, _main.omp_outlined@PAGE
Lloh3:
	add	x2, x2, _main.omp_outlined@PAGEOFF
	mov	x0, x19
	mov	w1, #2                          ; =0x2
	bl	___kmpc_fork_call
	add	x8, sp, #48
	stp	x21, x8, [sp]
Lloh4:
	adrp	x2, _main.omp_outlined.1@PAGE
Lloh5:
	add	x2, x2, _main.omp_outlined.1@PAGEOFF
	mov	x0, x19
	mov	w1, #2                          ; =0x2
	bl	___kmpc_fork_call
	movi.2d	v0, #0000000000000000
	movi.2s	v1, #2
	movi.2s	v2, #4
	mov	w8, #18725                      ; =0x4925
	movk	w8, #9362, lsl #16
	dup.2s	v3, w8
Lloh6:
	adrp	x8, lCPI0_0@PAGE
Lloh7:
	ldr	d4, [x8, lCPI0_0@PAGEOFF]
	movi.2s	v5, #6
	movi.2s	v6, #7
	movi.2s	v7, #8
	movi.2d	v16, #0000000000000000
	movi.2d	v17, #0000000000000000
	movi.2d	v18, #0000000000000000
LBB0_1:                                 ; =>This Inner Loop Header: Depth=1
	add.2s	v19, v4, v1
	add.2s	v20, v4, v2
	add.2s	v21, v4, v5
	umull.2d	v22, v4, v3
	shrn.2s	v22, v22, #32
	sub.2s	v23, v4, v22
	ushll.2d	v23, v23, #0
	shrn.2s	v23, v23, #1
	add.2s	v22, v23, v22
	ushr.2s	v22, v22, #2
	mov.16b	v23, v4
	mls.2s	v23, v22, v6
	umull.2d	v22, v19, v3
	shrn.2s	v22, v22, #32
	sub.2s	v24, v19, v22
	ushll.2d	v24, v24, #0
	shrn.2s	v24, v24, #1
	add.2s	v22, v24, v22
	ushr.2s	v22, v22, #2
	mls.2s	v19, v22, v6
	umull.2d	v22, v20, v3
	shrn.2s	v22, v22, #32
	sub.2s	v24, v20, v22
	ushll.2d	v24, v24, #0
	shrn.2s	v24, v24, #1
	add.2s	v22, v24, v22
	ushr.2s	v22, v22, #2
	mls.2s	v20, v22, v6
	umull.2d	v22, v21, v3
	shrn.2s	v22, v22, #32
	sub.2s	v24, v21, v22
	ushll.2d	v24, v24, #0
	shrn.2s	v24, v24, #1
	add.2s	v22, v24, v22
	ushr.2s	v22, v22, #2
	mls.2s	v21, v22, v6
	uaddw.2d	v0, v0, v23
	uaddw.2d	v16, v16, v19
	uaddw.2d	v17, v17, v20
	uaddw.2d	v18, v18, v21
	add.2s	v4, v4, v7
	subs	x20, x20, #8
	b.ne	LBB0_1
; %bb.2:
	add.2d	v0, v16, v0
	add.2d	v1, v18, v17
	add.2d	v0, v1, v0
	addp.2d	d0, v0
	str	q0, [sp, #16]                   ; 16-byte Folded Spill
	fmov	x19, d0
	bl	_omp_get_max_threads
                                        ; kill: def $w0 killed $w0 def $x0
	str	x0, [sp]
Lloh8:
	adrp	x0, l_.str@PAGE
Lloh9:
	add	x0, x0, l_.str@PAGEOFF
	bl	_printf
	ldr	q0, [sp, #16]                   ; 16-byte Folded Reload
	str	d0, [sp]
Lloh10:
	adrp	x0, l_.str.2@PAGE
Lloh11:
	add	x0, x0, l_.str.2@PAGEOFF
	bl	_printf
	ldur	x8, [x29, #-40]
Lloh12:
	adrp	x20, l_.str.5@PAGE
Lloh13:
	add	x20, x20, l_.str.5@PAGEOFF
Lloh14:
	adrp	x9, l_.str.4@PAGE
Lloh15:
	add	x9, x9, l_.str.4@PAGEOFF
	cmp	x8, x19
	csel	x9, x9, x20, eq
	stp	x8, x9, [sp]
Lloh16:
	adrp	x0, l_.str.3@PAGE
Lloh17:
	add	x0, x0, l_.str.3@PAGEOFF
	bl	_printf
	ldr	x8, [sp, #48]
Lloh18:
	adrp	x9, l_.str.7@PAGE
Lloh19:
	add	x9, x9, l_.str.7@PAGEOFF
	cmp	x8, x19
	csel	x9, x9, x20, eq
	stp	x8, x9, [sp]
Lloh20:
	adrp	x0, l_.str.6@PAGE
Lloh21:
	add	x0, x0, l_.str.6@PAGEOFF
	bl	_printf
	mov	w0, #0                          ; =0x0
	ldp	x29, x30, [sp, #96]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #80]             ; 16-byte Folded Reload
	ldp	x22, x21, [sp, #64]             ; 16-byte Folded Reload
	add	sp, sp, #112
	ret
	.loh AdrpLdr	Lloh6, Lloh7
	.loh AdrpAdd	Lloh4, Lloh5
	.loh AdrpAdd	Lloh2, Lloh3
	.loh AdrpAdd	Lloh0, Lloh1
	.loh AdrpAdd	Lloh20, Lloh21
	.loh AdrpAdd	Lloh18, Lloh19
	.loh AdrpAdd	Lloh16, Lloh17
	.loh AdrpAdd	Lloh14, Lloh15
	.loh AdrpAdd	Lloh12, Lloh13
	.loh AdrpAdd	Lloh10, Lloh11
	.loh AdrpAdd	Lloh8, Lloh9
	.cfi_endproc
                                        ; -- End function
	.section	__TEXT,__literal16,16byte_literals
	.p2align	4, 0x0                          ; -- Begin function main.omp_outlined
lCPI1_0:
	.quad	0                               ; 0x0
	.quad	1                               ; 0x1
	.section	__TEXT,__text,regular,pure_instructions
	.p2align	2
_main.omp_outlined:                     ; @main.omp_outlined
	.cfi_startproc
; %bb.0:
	sub	sp, sp, #96
	stp	x22, x21, [sp, #48]             ; 16-byte Folded Spill
	stp	x20, x19, [sp, #64]             ; 16-byte Folded Spill
	stp	x29, x30, [sp, #80]             ; 16-byte Folded Spill
	add	x29, sp, #80
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w19, -24
	.cfi_offset w20, -32
	.cfi_offset w21, -40
	.cfi_offset w22, -48
	mov	x19, x3
	mov	w21, #33919                     ; =0x847f
	movk	w21, #30, lsl #16
	stp	x21, xzr, [sp, #32]
	mov	w8, #1                          ; =0x1
	str	x8, [sp, #24]
	str	wzr, [sp, #20]
	ldr	w20, [x0]
	str	x8, [sp]
Lloh22:
	adrp	x0, l___unnamed_2@PAGE
Lloh23:
	add	x0, x0, l___unnamed_2@PAGEOFF
	add	x3, sp, #20
	add	x4, sp, #40
	add	x5, sp, #32
	add	x6, sp, #24
	mov	x1, x20
	mov	w2, #34                         ; =0x22
	mov	w7, #1                          ; =0x1
	bl	___kmpc_for_static_init_8
	ldp	x8, x14, [sp, #32]
	cmp	x8, x21
	csel	x8, x8, x21, lt
	str	x8, [sp, #32]
	cmp	x14, x8
	b.gt	LBB1_8
; %bb.1:
	ldr	x13, [x19]
	add	x8, x8, #1
	sub	x11, x8, x14
	mov	x9, #18725                      ; =0x4925
	movk	x9, #9362, lsl #16
	movk	x9, #37449, lsl #32
	movk	x9, #18724, lsl #48
	cmp	x11, #8
	b.hs	LBB1_3
; %bb.2:
	mov	x10, x14
	b	LBB1_6
LBB1_3:
	and	x12, x11, #0xfffffffffffffff8
	add	x10, x14, x12
	movi.2d	v0, #0000000000000000
	movi.2d	v1, #0000000000000000
	mov.d	v1[0], x13
	dup.2d	v2, x14
Lloh24:
	adrp	x13, lCPI1_0@PAGE
Lloh25:
	ldr	q3, [x13, lCPI1_0@PAGEOFF]
	add.2d	v2, v2, v3
	mov	w13, #2                         ; =0x2
	dup.2d	v3, x13
	mov	w13, #4                         ; =0x4
	dup.2d	v4, x13
	mov	w13, #6                         ; =0x6
	dup.2d	v5, x13
	mov	w13, #8                         ; =0x8
	dup.2d	v6, x13
	mov	x13, x12
	movi.2d	v7, #0000000000000000
	movi.2d	v16, #0000000000000000
LBB1_4:                                 ; =>This Inner Loop Header: Depth=1
	add.2d	v17, v2, v3
	add.2d	v18, v2, v4
	add.2d	v19, v2, v5
	mov.d	x14, v2[1]
	smulh	x15, x14, x9
	asr	x16, x15, #1
	add	x15, x16, x15, lsr #63
	sub	x15, x15, x15, lsl #3
	add	x14, x14, x15
	fmov	x15, d2
	smulh	x16, x15, x9
	asr	x17, x16, #1
	add	x16, x17, x16, lsr #63
	sub	x16, x16, x16, lsl #3
	add	x15, x15, x16
	fmov	d20, x15
	mov.d	v20[1], x14
	mov.d	x14, v17[1]
	smulh	x15, x14, x9
	asr	x16, x15, #1
	add	x15, x16, x15, lsr #63
	sub	x15, x15, x15, lsl #3
	add	x14, x14, x15
	fmov	x15, d17
	smulh	x16, x15, x9
	asr	x17, x16, #1
	add	x16, x17, x16, lsr #63
	sub	x16, x16, x16, lsl #3
	add	x15, x15, x16
	fmov	d17, x15
	mov.d	v17[1], x14
	mov.d	x14, v18[1]
	smulh	x15, x14, x9
	asr	x16, x15, #1
	add	x15, x16, x15, lsr #63
	sub	x15, x15, x15, lsl #3
	add	x14, x14, x15
	fmov	x15, d18
	smulh	x16, x15, x9
	asr	x17, x16, #1
	add	x16, x17, x16, lsr #63
	sub	x16, x16, x16, lsl #3
	add	x15, x15, x16
	fmov	d18, x15
	mov.d	v18[1], x14
	mov.d	x14, v19[1]
	smulh	x15, x14, x9
	asr	x16, x15, #1
	add	x15, x16, x15, lsr #63
	sub	x15, x15, x15, lsl #3
	add	x14, x14, x15
	fmov	x15, d19
	smulh	x16, x15, x9
	asr	x17, x16, #1
	add	x16, x17, x16, lsr #63
	sub	x16, x16, x16, lsl #3
	add	x15, x15, x16
	fmov	d19, x15
	mov.d	v19[1], x14
	add.2d	v1, v1, v20
	add.2d	v0, v0, v17
	add.2d	v7, v7, v18
	add.2d	v16, v16, v19
	add.2d	v2, v2, v6
	subs	x13, x13, #8
	b.ne	LBB1_4
; %bb.5:
	add.2d	v0, v0, v1
	add.2d	v0, v7, v0
	add.2d	v0, v16, v0
	addp.2d	d0, v0
	fmov	x13, d0
	cmp	x11, x12
	b.eq	LBB1_7
LBB1_6:                                 ; =>This Inner Loop Header: Depth=1
	smulh	x11, x10, x9
	asr	x12, x11, #1
	add	x11, x12, x11, lsr #63
	sub	x11, x11, x11, lsl #3
	add	x12, x13, x10
	add	x13, x12, x11
	add	x10, x10, #1
	cmp	x8, x10
	b.ne	LBB1_6
LBB1_7:
	str	x13, [x19]
LBB1_8:
Lloh26:
	adrp	x0, l___unnamed_2@PAGE
Lloh27:
	add	x0, x0, l___unnamed_2@PAGEOFF
	mov	x1, x20
	bl	___kmpc_for_static_fini
	ldp	x29, x30, [sp, #80]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #64]             ; 16-byte Folded Reload
	ldp	x22, x21, [sp, #48]             ; 16-byte Folded Reload
	add	sp, sp, #96
	ret
	.loh AdrpAdd	Lloh22, Lloh23
	.loh AdrpLdr	Lloh24, Lloh25
	.loh AdrpAdd	Lloh26, Lloh27
	.cfi_endproc
                                        ; -- End function
	.section	__TEXT,__literal16,16byte_literals
	.p2align	4, 0x0                          ; -- Begin function main.omp_outlined.1
lCPI2_0:
	.quad	0                               ; 0x0
	.quad	1                               ; 0x1
	.section	__TEXT,__text,regular,pure_instructions
	.p2align	2
_main.omp_outlined.1:                   ; @main.omp_outlined.1
	.cfi_startproc
; %bb.0:
	sub	sp, sp, #112
	stp	x22, x21, [sp, #64]             ; 16-byte Folded Spill
	stp	x20, x19, [sp, #80]             ; 16-byte Folded Spill
	stp	x29, x30, [sp, #96]             ; 16-byte Folded Spill
	add	x29, sp, #96
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w19, -24
	.cfi_offset w20, -32
	.cfi_offset w21, -40
	.cfi_offset w22, -48
	mov	x19, x3
Lloh28:
	adrp	x8, ___stack_chk_guard@GOTPAGE
Lloh29:
	ldr	x8, [x8, ___stack_chk_guard@GOTPAGEOFF]
Lloh30:
	ldr	x8, [x8]
	stur	x8, [x29, #-40]
	mov	w21, #33919                     ; =0x847f
	movk	w21, #30, lsl #16
	stp	x21, xzr, [sp, #32]
	mov	w8, #1                          ; =0x1
	str	x8, [sp, #24]
	str	wzr, [sp, #20]
	ldr	w20, [x0]
	str	x8, [sp]
Lloh31:
	adrp	x0, l___unnamed_2@PAGE
Lloh32:
	add	x0, x0, l___unnamed_2@PAGEOFF
	add	x3, sp, #20
	add	x4, sp, #40
	add	x5, sp, #32
	add	x6, sp, #24
	mov	x1, x20
	mov	w2, #34                         ; =0x22
	mov	w7, #1                          ; =0x1
	bl	___kmpc_for_static_init_8
	mov	x13, #0                         ; =0x0
	ldp	x8, x14, [sp, #32]
	cmp	x8, x21
	csel	x8, x8, x21, lt
	str	x8, [sp, #32]
	cmp	x14, x8
	b.gt	LBB2_7
; %bb.1:
	add	x8, x8, #1
	sub	x11, x8, x14
	mov	x9, #18725                      ; =0x4925
	movk	x9, #9362, lsl #16
	movk	x9, #37449, lsl #32
	movk	x9, #18724, lsl #48
	cmp	x11, #8
	b.hs	LBB2_3
; %bb.2:
	mov	x13, #0                         ; =0x0
	mov	x10, x14
	b	LBB2_6
LBB2_3:
	and	x12, x11, #0xfffffffffffffff8
	add	x10, x14, x12
	dup.2d	v0, x14
Lloh33:
	adrp	x13, lCPI2_0@PAGE
Lloh34:
	ldr	q1, [x13, lCPI2_0@PAGEOFF]
	add.2d	v1, v0, v1
	movi.2d	v0, #0000000000000000
	mov	w13, #2                         ; =0x2
	dup.2d	v2, x13
	mov	w13, #4                         ; =0x4
	dup.2d	v3, x13
	mov	w13, #6                         ; =0x6
	dup.2d	v4, x13
	mov	w13, #8                         ; =0x8
	dup.2d	v5, x13
	mov	x13, x12
	movi.2d	v6, #0000000000000000
	movi.2d	v7, #0000000000000000
	movi.2d	v16, #0000000000000000
LBB2_4:                                 ; =>This Inner Loop Header: Depth=1
	add.2d	v17, v1, v2
	add.2d	v18, v1, v3
	add.2d	v19, v1, v4
	mov.d	x14, v1[1]
	smulh	x15, x14, x9
	asr	x16, x15, #1
	add	x15, x16, x15, lsr #63
	sub	x15, x15, x15, lsl #3
	add	x14, x14, x15
	fmov	x15, d1
	smulh	x16, x15, x9
	asr	x17, x16, #1
	add	x16, x17, x16, lsr #63
	sub	x16, x16, x16, lsl #3
	add	x15, x15, x16
	fmov	d20, x15
	mov.d	v20[1], x14
	mov.d	x14, v17[1]
	smulh	x15, x14, x9
	asr	x16, x15, #1
	add	x15, x16, x15, lsr #63
	sub	x15, x15, x15, lsl #3
	add	x14, x14, x15
	fmov	x15, d17
	smulh	x16, x15, x9
	asr	x17, x16, #1
	add	x16, x17, x16, lsr #63
	sub	x16, x16, x16, lsl #3
	add	x15, x15, x16
	fmov	d17, x15
	mov.d	v17[1], x14
	mov.d	x14, v18[1]
	smulh	x15, x14, x9
	asr	x16, x15, #1
	add	x15, x16, x15, lsr #63
	sub	x15, x15, x15, lsl #3
	add	x14, x14, x15
	fmov	x15, d18
	smulh	x16, x15, x9
	asr	x17, x16, #1
	add	x16, x17, x16, lsr #63
	sub	x16, x16, x16, lsl #3
	add	x15, x15, x16
	fmov	d18, x15
	mov.d	v18[1], x14
	mov.d	x14, v19[1]
	smulh	x15, x14, x9
	asr	x16, x15, #1
	add	x15, x16, x15, lsr #63
	sub	x15, x15, x15, lsl #3
	add	x14, x14, x15
	fmov	x15, d19
	smulh	x16, x15, x9
	asr	x17, x16, #1
	add	x16, x17, x16, lsr #63
	sub	x16, x16, x16, lsl #3
	add	x15, x15, x16
	fmov	d19, x15
	mov.d	v19[1], x14
	add.2d	v0, v0, v20
	add.2d	v6, v6, v17
	add.2d	v7, v7, v18
	add.2d	v16, v16, v19
	add.2d	v1, v1, v5
	subs	x13, x13, #8
	b.ne	LBB2_4
; %bb.5:
	add.2d	v0, v6, v0
	add.2d	v0, v7, v0
	add.2d	v0, v16, v0
	addp.2d	d0, v0
	fmov	x13, d0
	cmp	x11, x12
	b.eq	LBB2_7
LBB2_6:                                 ; =>This Inner Loop Header: Depth=1
	smulh	x11, x10, x9
	asr	x12, x11, #1
	add	x11, x12, x11, lsr #63
	sub	x11, x11, x11, lsl #3
	add	x12, x13, x10
	add	x13, x12, x11
	add	x10, x10, #1
	cmp	x8, x10
	b.ne	LBB2_6
LBB2_7:
	str	x13, [sp, #8]
Lloh35:
	adrp	x0, l___unnamed_2@PAGE
Lloh36:
	add	x0, x0, l___unnamed_2@PAGEOFF
	mov	x1, x20
	bl	___kmpc_for_static_fini
	add	x8, sp, #8
	str	x8, [sp, #48]
Lloh37:
	adrp	x0, l___unnamed_3@PAGE
Lloh38:
	add	x0, x0, l___unnamed_3@PAGEOFF
Lloh39:
	adrp	x5, _main.omp_outlined.1.omp.reduction.reduction_func@PAGE
Lloh40:
	add	x5, x5, _main.omp_outlined.1.omp.reduction.reduction_func@PAGEOFF
Lloh41:
	adrp	x6, _.gomp_critical_user_.reduction.var@GOTPAGE
Lloh42:
	ldr	x6, [x6, _.gomp_critical_user_.reduction.var@GOTPAGEOFF]
	add	x4, sp, #48
	mov	x1, x20
	mov	w2, #1                          ; =0x1
	mov	w3, #8                          ; =0x8
	bl	___kmpc_reduce_nowait
	cmp	w0, #2
	b.eq	LBB2_10
; %bb.8:
	cmp	w0, #1
	b.ne	LBB2_11
; %bb.9:
	ldr	x8, [x19]
	ldr	x9, [sp, #8]
	add	x8, x9, x8
	str	x8, [x19]
Lloh43:
	adrp	x0, l___unnamed_3@PAGE
Lloh44:
	add	x0, x0, l___unnamed_3@PAGEOFF
Lloh45:
	adrp	x2, _.gomp_critical_user_.reduction.var@GOTPAGE
Lloh46:
	ldr	x2, [x2, _.gomp_critical_user_.reduction.var@GOTPAGEOFF]
	mov	x1, x20
	bl	___kmpc_end_reduce_nowait
	b	LBB2_11
LBB2_10:
	ldr	x8, [sp, #8]
	ldadd	x8, x8, [x19]
LBB2_11:
	ldur	x8, [x29, #-40]
Lloh47:
	adrp	x9, ___stack_chk_guard@GOTPAGE
Lloh48:
	ldr	x9, [x9, ___stack_chk_guard@GOTPAGEOFF]
Lloh49:
	ldr	x9, [x9]
	cmp	x9, x8
	b.ne	LBB2_13
; %bb.12:
	ldp	x29, x30, [sp, #96]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #80]             ; 16-byte Folded Reload
	ldp	x22, x21, [sp, #64]             ; 16-byte Folded Reload
	add	sp, sp, #112
	ret
LBB2_13:
	bl	___stack_chk_fail
	.loh AdrpAdd	Lloh31, Lloh32
	.loh AdrpLdrGotLdr	Lloh28, Lloh29, Lloh30
	.loh AdrpLdr	Lloh33, Lloh34
	.loh AdrpLdrGot	Lloh41, Lloh42
	.loh AdrpAdd	Lloh39, Lloh40
	.loh AdrpAdd	Lloh37, Lloh38
	.loh AdrpAdd	Lloh35, Lloh36
	.loh AdrpLdrGot	Lloh45, Lloh46
	.loh AdrpAdd	Lloh43, Lloh44
	.loh AdrpLdrGotLdr	Lloh47, Lloh48, Lloh49
	.cfi_endproc
                                        ; -- End function
	.p2align	2                               ; -- Begin function main.omp_outlined.1.omp.reduction.reduction_func
_main.omp_outlined.1.omp.reduction.reduction_func: ; @main.omp_outlined.1.omp.reduction.reduction_func
	.cfi_startproc
; %bb.0:
	ldr	x8, [x1]
	ldr	x9, [x0]
	ldr	x10, [x9]
	ldr	x8, [x8]
	add	x8, x8, x10
	str	x8, [x9]
	ret
	.cfi_endproc
                                        ; -- End function
	.section	__TEXT,__cstring,cstring_literals
l___unnamed_4:                          ; @0
	.asciz	";unknown;unknown;0;0;;"

	.section	__DATA,__const
	.p2align	3, 0x0                          ; @1
l___unnamed_2:
	.long	0                               ; 0x0
	.long	514                             ; 0x202
	.long	0                               ; 0x0
	.long	22                              ; 0x16
	.quad	l___unnamed_4

	.p2align	3, 0x0                          ; @2
l___unnamed_1:
	.long	0                               ; 0x0
	.long	2                               ; 0x2
	.long	0                               ; 0x0
	.long	22                              ; 0x16
	.quad	l___unnamed_4

	.comm	_.gomp_critical_user_.reduction.var,32,3 ; @.gomp_critical_user_.reduction.var
	.p2align	3, 0x0                          ; @3
l___unnamed_3:
	.long	0                               ; 0x0
	.long	18                              ; 0x12
	.long	0                               ; 0x0
	.long	22                              ; 0x16
	.quad	l___unnamed_4

	.section	__TEXT,__cstring,cstring_literals
l_.str:                                 ; @.str
	.asciz	"threads=%d\n"

l_.str.2:                               ; @.str.2
	.asciz	"sequencial (referencia) = %ld\n"

l_.str.3:                               ; @.str.3
	.asciz	"parallel for (corrida)  = %ld   %s\n"

l_.str.4:                               ; @.str.4
	.space	1

l_.str.5:                               ; @.str.5
	.asciz	"<-- ERRADO"

l_.str.6:                               ; @.str.6
	.asciz	"com reduction           = %ld   %s\n"

l_.str.7:                               ; @.str.7
	.asciz	"OK"

.subsections_via_symbols
